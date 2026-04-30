import type { Customer, DashboardStats, LoginRequest, Order, OrderStatus, ProductCategory, TokenResponse, Conversation, Message } from "./types";
const API = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const tok = () => localStorage.getItem("access_token");
async function req<T>(path: string, opt: RequestInit={}): Promise<T> {
  const h: Record<string,string> = {"Content-Type":"application/json",...(opt.headers as Record<string,string>)};
  if(tok()) h["Authorization"]=`Bearer ${tok()}`;
  let r = await fetch(`${API}${path}`,{...opt,headers:h});
  if(r.status===401){const ok=await tryRefresh();if(ok){h["Authorization"]=`Bearer ${tok()}`;r=await fetch(`${API}${path}`,{...opt,headers:h});}else{localStorage.clear();window.location.href="/login";throw new Error("Sessão expirada");}}
  if(!r.ok){const e=await r.json().catch(()=>({detail:r.statusText}));throw new Error(e.detail??`HTTP ${r.status}`);}
  return r.json();
}
async function tryRefresh(){const t=localStorage.getItem("refresh_token");if(!t)return false;try{const r=await fetch(`${API}/api/auth/refresh`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({refresh_token:t})});if(!r.ok)return false;const d:TokenResponse=await r.json();localStorage.setItem("access_token",d.access_token);localStorage.setItem("refresh_token",d.refresh_token);return true;}catch{return false;}}
export const authApi={login:async(b:LoginRequest):Promise<TokenResponse>=>{const r=await fetch(`${API}/api/auth/login`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(b)});if(!r.ok){const e=await r.json().catch(()=>({}));throw new Error(e.detail??"Erro ao fazer login");}return r.json();}};
export const dashboardApi={getStats:():Promise<DashboardStats>=>req("/api/dashboard/stats")};
export const ordersApi={list:(status?:OrderStatus,limit=50):Promise<Order[]>=>{const p=new URLSearchParams({limit:String(limit)});if(status)p.set("status_filter",status);return req(`/api/orders/?${p}`);},get:(id:string):Promise<Order>=>req(`/api/orders/${id}`),updateStatus:(id:string,status:OrderStatus):Promise<Order>=>req(`/api/orders/${id}/status`,{method:"PATCH",body:JSON.stringify({status})})};
export const productsApi={listCategories:():Promise<ProductCategory[]>=>req("/api/products/categories"),updateProduct:(id:string,data:object)=>req(`/api/products/${id}`,{method:"PATCH",body:JSON.stringify(data)})};
export const customersApi={list:(limit=50):Promise<Customer[]>=>req(`/api/customers/?limit=${limit}`),toggleBlock:(id:string,is_blocked:boolean):Promise<Customer>=>req(`/api/customers/${id}`,{method:"PATCH",body:JSON.stringify({is_blocked})})};
export const conversationsApi={list:(limit=30):Promise<Conversation[]>=>req(`/api/conversations/?limit=${limit}`),getMessages:(id:string):Promise<Message[]>=>req(`/api/conversations/${id}/messages`),takeover:(id:string):Promise<void>=>req(`/api/conversations/${id}/takeover`,{method:"POST"})};
