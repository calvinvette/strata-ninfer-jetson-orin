import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from owner_observations import PREFIX, summarize


def event(kind, address=100, size=0, instance=1, device=0):
    return PREFIX + json.dumps(dict(schema=1, owner='verifier', kind=kind,
        allocation=address, requested_bytes=size, instance=instance,
        device=device, count=1 if kind in ('graph_instantiate', 'view') else 0))


def reservation(label, size, instance=1, device=0):
    return PREFIX + json.dumps(dict(schema=1, owner=label, kind='reservation',
        allocation=0, requested_bytes=size, instance=instance, device=device, count=0))


class OwnerObservationTests(unittest.TestCase):
    def test_reused_address_and_concurrent_arena_peaks(self):
        result = summarize([event('allocate', size=10), event('allocate', 200, 20),
            event('free'), event('allocate', size=5), event('free', 200), event('free'),
            event('graph_instantiate', 0)])
        self.assertEqual(result['owners'][0]['peak_observed_requested_bytes'], 30)
        self.assertEqual(result['owners'][0]['live_observed_requested_bytes'], 0)
        self.assertEqual(result['owners'][0]['successful_graph_instantiations'], 1)

    def test_pinned_and_pageable_expert_staging_are_separate_host_owners(self):
        rows = []
        for owner, address, size in [('expert-stage-pinned-host', 301, 4096),
                                     ('expert-stage-pageable-host', 302, 8192)]:
            rows.extend([PREFIX + json.dumps(dict(schema=1, owner=owner, kind='allocate',
                allocation=address, requested_bytes=size, instance=9, device=-1, count=0)),
                PREFIX + json.dumps(dict(schema=1, owner=owner, kind='free',
                allocation=address, requested_bytes=0, instance=9, device=-1, count=0))])
        result = summarize(rows)
        self.assertEqual(result['allocation_events'], 2)
        self.assertEqual(result['free_events'], 2)
        self.assertEqual({row['owner'] for row in result['owners']},
                         {'expert-stage-pinned-host', 'expert-stage-pageable-host'})
        self.assertTrue(all(row['live_observed_requested_bytes'] == 0 for row in result['owners']))

    def test_segmented_vmm_tracks_mapped_handles_across_shrink_and_regrow(self):
        def vmm(kind, handle, size=0):
            return PREFIX + json.dumps(dict(schema=1, owner='expert-cache-vmm-segment',
                kind=kind, allocation=handle, requested_bytes=size, instance=11,
                device=0, count=0))

        rows = [vmm('allocate', 501, 8 << 20), vmm('allocate', 502, 8 << 20),
                vmm('free', 502), vmm('allocate', 503, 8 << 20),
                vmm('free', 501), vmm('free', 503)]
        result = summarize(rows)
        owner = result['owners'][0]
        self.assertEqual(owner['owner'], 'expert-cache-vmm-segment')
        self.assertEqual(owner['peak_observed_requested_bytes'], 16 << 20)
        self.assertEqual(owner['live_observed_requested_bytes'], 0)
        self.assertEqual(result['allocation_events'], 3)
        self.assertEqual(result['free_events'], 3)
        self.assertIn('CUDA segmented ExpertCache mapped VMM physical segments', result['coverage'])

    def test_shared_vmm_chunk_lifetime_is_independent_of_range_owner(self):
        def chunk(kind, handle, size=0):
            return PREFIX + json.dumps(dict(schema=1, owner='cuda-vmm-physical-chunk',
                kind=kind, allocation=handle, requested_bytes=size, instance=7,
                device=0, count=0))

        # The same physical handle can be unmapped from one range and mapped in
        # another without ending its allocation lifetime.
        rows = [chunk('allocate', 700, 2 << 20), event('view', 700, 2 << 20, instance=8),
                event('view', 700, 2 << 20, instance=9), chunk('free', 700)]
        result = summarize(rows)
        backing = next(o for o in result['owners'] if o['owner'] == 'cuda-vmm-physical-chunk')
        self.assertEqual(backing['peak_observed_requested_bytes'], 2 << 20)
        self.assertEqual(backing['live_observed_requested_bytes'], 0)
        self.assertEqual(backing['view_events'], 0)
        self.assertEqual(result['allocation_events'], 1)
        self.assertEqual(result['free_events'], 1)

    def test_alias_cannot_be_counted_as_another_allocation(self):
        with self.assertRaises(ValueError):
            summarize([event('allocate', size=10), event('allocate', size=10, instance=2)])

    def test_conflicting_free_cannot_hide_live_ownership(self):
        with self.assertRaises(ValueError):
            summarize([event('allocate', size=10), event('free', instance=2)])

    def test_absent_trace_is_not_zero_memory(self):
        with self.assertRaises(ValueError):
            summarize(['strata verify: ordinary log'])

    def test_incomplete_teardown_remains_live(self):
        result = summarize([event('allocate', size=10)])
        self.assertEqual(result['owners'][0]['live_observed_requested_bytes'], 10)

    def test_overlapping_and_repeated_views_do_not_duplicate_backing(self):
        result = summarize([event('allocate', size=100), event('view', size=100),
                            event('view', 101, 90), event('view', size=100), event('free')])
        self.assertEqual(result['allocation_events'], 1)
        self.assertEqual(result['owners'][0]['peak_observed_requested_bytes'], 100)
        self.assertEqual(result['owners'][0]['live_observed_requested_bytes'], 0)
        self.assertEqual(result['owners'][0]['view_events'], 3)

    def test_borrowed_external_view_does_not_invent_parent_ownership(self):
        result = summarize([event('allocate', size=10), event('view', 999, 1000, instance=2)])
        external = next(o for o in result['owners'] if o['instance'] == 2)
        self.assertEqual(external['peak_observed_requested_bytes'], 0)
        self.assertEqual(external['view_events'], 1)

    def test_owner_payload_counter_does_not_duplicate_observed_arena(self):
        result = summarize([event('allocate', size=10),
                            event('payload_snapshot', 0, 200), event('free')])
        self.assertEqual(result['owners'][0]['peak_observed_requested_bytes'], 10)
        self.assertEqual(result['owners'][0]['last_owner_reported_payload_bytes'], 200)

    def test_planned_workspace_reservations_stay_separate_from_allocations(self):
        result = summarize([event('allocate', size=100),
                            reservation('expert-cache.prefill-workspace', 40),
                            reservation('expert-cache.mtp-bind', 20), event('free')])
        self.assertEqual(result['allocation_events'], 1)
        self.assertEqual(result['owners'][0]['peak_observed_requested_bytes'], 100)
        self.assertEqual(sum(r['bytes'] for r in result['planned_reservations']['events']), 60)
        self.assertIn('never added', result['planned_reservations']['scope'])

    def test_duplicate_planned_reservation_label_is_rejected(self):
        with self.assertRaises(ValueError):
            summarize([event('allocate', size=1), reservation('cache.prefill', 2),
                       reservation('cache.prefill', 3)])

    @unittest.skipUnless(shutil.which('c++'), 'C++ compiler unavailable')
    def test_cpp_opt_in_is_silent_by_default_and_emits_parseable_records(self):
        root = Path(__file__).resolve().parents[2]
        source = '''#include "strata/platform/integration_trace.hpp"
int main() {
  int allocation;
  strata::platform::integration_trace::event("verifier", "allocate", &allocation, &allocation, 32, 0);
  strata::platform::integration_trace::event("verifier", "view", &allocation, &allocation, 16, 0, 1);
  strata::platform::integration_trace::reservation("expert-cache.prefill-workspace", &allocation, 64, 0);
  strata::platform::integration_trace::event("verifier", "free", &allocation, &allocation, 0, 0);
}'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'test.cpp').write_text(source)
            subprocess.run(['c++', '-std=c++20', '-I', str(root / 'include'),
                str(path / 'test.cpp'), '-o', str(path / 'test')], check=True, capture_output=True)
            env = dict(os.environ)
            env.pop('STRATA_INTEGRATION_TRACE', None)
            off = subprocess.run([str(path / 'test')], env=env, check=True, capture_output=True, text=True)
            self.assertEqual(off.stderr, '')
            for setting in ('0', 'true', '10'):
                env['STRATA_INTEGRATION_TRACE'] = setting
                self.assertEqual(subprocess.run([str(path / 'test')], env=env,
                    check=True, capture_output=True, text=True).stderr, '')
            env['STRATA_INTEGRATION_TRACE'] = '1'
            on = subprocess.run([str(path / 'test')], env=env, check=True, capture_output=True, text=True)
            result = summarize(on.stderr.splitlines())
            self.assertEqual(result['allocation_events'], 1)
            self.assertEqual(result['free_events'], 1)
            self.assertEqual(result['owners'][0]['live_observed_requested_bytes'], 0)
            self.assertEqual(result['owners'][0]['view_events'], 1)
            self.assertEqual(result['planned_reservations']['events'][0]['bytes'], 64)
