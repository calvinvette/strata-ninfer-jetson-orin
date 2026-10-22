#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>
struct H { char magic[8]; uint32_t ver; int32_t layer; int64_t pos; uint64_t recurrent, count; int32_t token, slot; };
struct R { H h{}; std::vector<float> v; };
using Key = std::tuple<int,int64_t,int>;
std::vector<R> read(const std::string& p) {
 std::ifstream f(p,std::ios::binary); if(!f) throw std::runtime_error("open "+p); std::vector<R> out;
 for(;;){R r; f.read((char*)&r.h,sizeof(H)); if(f.eof()) break; if(!f||std::memcmp(r.h.magic,"STGCMT1",7)||r.h.ver!=1) throw std::runtime_error("bad header "+p); r.v.resize(r.h.count); f.read((char*)r.v.data(),r.v.size()*4); if(!f) throw std::runtime_error("short payload "+p); out.push_back(std::move(r));} return out;
}
struct M { uint64_t changed=0,n=0; double err=0,ref=0,maxabs=0; void add(float a,float b){double d=(double)a-b; changed+=d!=0; ++n; err+=d*d; ref+=(double)a*a; maxabs=std::max(maxabs,std::abs(d));} void merge(const M&x){changed+=x.changed;n+=x.n;err+=x.err;ref+=x.ref;maxabs=std::max(maxabs,x.maxabs);} double rel()const{return ref?std::sqrt(err/ref):0;} };
M compare(const R&a,const R&b){M m; if(a.v.size()!=b.v.size()) throw std::runtime_error("count mismatch"); for(size_t i=0;i<a.v.size();i++)m.add(a.v[i],b.v[i]); return m;}
struct Group { int slot=-1,token=-1,last_layer=-1,layers=0; int64_t pos=-1; M total[2],layer6[2]; };
void print(const Group&g){if(!g.layers)return;int q=g.total[0].rel()<=g.total[1].rel()?0:1;std::cout<<"slot="<<g.slot<<" position="<<g.pos<<" token="<<g.token<<" layers="<<g.layers<<" nearest_prompt="<<q<<" all_layer_rel_l2="<<g.total[q].rel()<<" other_prompt_rel_l2="<<g.total[1-q].rel()<<" changed="<<g.total[q].changed<<"/"<<g.total[q].n;if(g.layer6[q].n)std::cout<<" layer6_rel_l2="<<g.layer6[q].rel();std::cout<<"\n";}
int main(int argc,char**argv){try{if(argc!=2)throw std::runtime_error("usage: analyzer RESULT_DIRECTORY");std::string root=argv[1];auto s0=read(root+"/run-alllayer-targetonly-commit-state/serial-slot-0.stgcmt");auto s1=read(root+"/run-alllayer-targetonly-commit-state/serial-slot-1.stgcmt");auto b=read(root+"/run-alllayer-targetonly-commit-state/batch.stgcmt");std::map<Key,const R*> refs[2];for(auto&r:s0)refs[0][{r.h.layer,r.h.pos,r.h.token}]=&r;for(auto&r:s1)refs[1][{r.h.layer,r.h.pos,r.h.token}]=&r;std::cout<<"records serial0="<<s0.size()<<" serial1="<<s1.size()<<" batch="<<b.size()<<"\n";Group g;for(auto&r:b){bool start=g.layers==0||r.h.slot!=g.slot||r.h.pos!=g.pos||r.h.layer<=g.last_layer;if(start){print(g);g=Group{};g.slot=r.h.slot;g.pos=r.h.pos;g.token=r.h.token;}Key k{r.h.layer,r.h.pos,r.h.token};for(int q=0;q<2;q++){auto it=refs[q].find(k);if(it!=refs[q].end()){M m=compare(*it->second,r);g.total[q].merge(m);if(r.h.layer==6)g.layer6[q]=m;}}g.layers++;g.last_layer=r.h.layer;}print(g); }catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}}
