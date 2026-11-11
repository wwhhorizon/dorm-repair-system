export const categories={water:'水路故障',electric:'电路与照明',door:'门窗故障',furniture:'家具损坏',other:'其他问题'};
export const states={pending:'待受理',assigned:'已派单',working:'处理中',review:'待验收',completed:'已完成',cancelled:'已取消'};
export const roles={student:'学生',admin:'管理员',technician:'维修人员'};
export const state={user:null,page:'dashboard',locations:[],users:[],filters:{},listPage:1,register:false,detail:null};
export async function api(path,options={}){
 const res=await fetch('/api'+path,{credentials:'same-origin',...options,headers:{'X-Requested-With':'RepairApp',...(options.body instanceof FormData?{}:{'Content-Type':'application/json'}),...options.headers}});
 if(!res.ok){let e;try{e=await res.json()}catch{e={message:'请求失败，请重试'}};throw new Error(e.message||'请求失败')}
 return res.status===204?null:res.json();
}
export const send=(path,body,method='POST')=>api(path,{method,body:JSON.stringify(body)});
export function query(filters=state.filters){const p=new URLSearchParams();for(const [k,v]of Object.entries(filters))if(v)p.set(k,v);return p.toString()}
export function utcDate(value,end=false){return value?new Date(value+(end?'T23:59:59':'T00:00:00')).toISOString():''}
