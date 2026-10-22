#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

struct CommitHeader { char magic[8]; uint32_t version; int32_t layer; int64_t position; uint64_t recurrent, count; int32_t token, slot; };
struct StateHeader { char magic[8]; uint64_t cells, layers, floats_per_layer; };
struct M { uint64_t changed=0,n=0; double err=0,ref=0,maxabs=0;
    void add(float a,float b){double d=(double)a-b;changed+=a!=b;++n;err+=d*d;ref+=(double)a*a;maxabs=std::max(maxabs,std::abs(d));}
    void merge(const M& x){changed+=x.changed;n+=x.n;err+=x.err;ref+=x.ref;maxabs=std::max(maxabs,x.maxabs);}
    double rel()const{return ref?std::sqrt(err/ref):0;}
};
std::vector<float> read_state(const std::string& path, StateHeader& h){
    std::ifstream f(path,std::ios::binary);if(!f)throw std::runtime_error("open "+path);
    f.read(reinterpret_cast<char*>(&h),sizeof(h));
    if(!f||std::memcmp(h.magic,"STGDN01",7))throw std::runtime_error("invalid state header "+path);
    std::vector<float> v((size_t)(h.layers*h.floats_per_layer));
    f.read(reinterpret_cast<char*>(v.data()),(std::streamsize)(v.size()*sizeof(float)));
    if(!f)throw std::runtime_error("truncated state "+path);return v;
}
int main(int argc,char**argv){try{
    if(argc!=4)throw std::runtime_error("usage: comparator RESULT_ROOT PROMPT0_TOKEN_AT_INDEX8 PROMPT1_TOKEN_AT_INDEX8");
    const std::string root=argv[1];const int token0=std::stoi(argv[2]),token1=std::stoi(argv[3]);
    StateHeader sh[2]{};
    auto serial0=read_state(root+"/run-mtp2-serial-state-at77/serial-slot-0.gdn",sh[0]);
    auto serial1=read_state(root+"/run-mtp2-serial-state-at77/serial-slot-1.gdn",sh[1]);
    if(sh[0].cells!=77||sh[1].cells!=77||sh[0].layers!=36||sh[1].layers!=36||
       sh[0].floats_per_layer!=sh[1].floats_per_layer)throw std::runtime_error("serial state geometry mismatch");
    std::ifstream f(root+"/run-mtp2-first-state-drift-supervised/batch-mtp2.stgcmt",std::ios::binary);
    if(!f)throw std::runtime_error("open batch committed-state file");
    M total[2];int first_layer[2]={-1,-1};M first_metrics[2];size_t records[2]={};
    for(;;){CommitHeader h{};f.read(reinterpret_cast<char*>(&h),sizeof(h));if(f.eof())break;
        if(!f||std::memcmp(h.magic,"STGCMT1",7)||h.version!=1)throw std::runtime_error("invalid batch header");
        std::vector<float> b((size_t)h.count);f.read(reinterpret_cast<char*>(b.data()),(std::streamsize)(b.size()*sizeof(float)));
        if(!f)throw std::runtime_error("truncated batch payload");
        if(h.position!=76)continue;
        int q=h.token==token0?0:h.token==token1?1:-1;if(q<0)continue;
        const size_t ordinal=(size_t)h.layer-(size_t)(h.layer+1)/4;
        if(ordinal>=sh[q].layers||b.size()!=sh[q].floats_per_layer)throw std::runtime_error("batch/serial geometry mismatch");
        M layer;
        const std::vector<float>& ref=q==0?serial0:serial1;
        const size_t at=ordinal*(size_t)sh[q].floats_per_layer;
        for(size_t i=0;i<b.size();++i)layer.add(ref[at+i],b[i]);
        total[q].merge(layer);++records[q];
        if(layer.changed&&first_layer[q]<0){first_layer[q]=h.layer;first_metrics[q]=layer;}
    }
    for(int q=0;q<2;++q){std::cout<<"prompt="<<q<<" token_at_position76="<<(q?token1:token0)
        <<" batch_layer_records="<<records[q]<<" total_rel_l2="<<total[q].rel()
        <<" changed="<<total[q].changed<<"/"<<total[q].n;
        if(first_layer[q]>=0)std::cout<<" first_changed_model_layer="<<first_layer[q]
          <<" layer_rel_l2="<<first_metrics[q].rel()<<" layer_changed="<<first_metrics[q].changed
          <<"/"<<first_metrics[q].n<<" layer_max_abs="<<first_metrics[q].maxabs;
        else std::cout<<" all_exact="<<(records[q]==36?"true":"incomplete");
        std::cout<<"\n";}
    return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}}
