import { create } from "zustand";
import { authApi } from "@/lib/api";
import type { LoginRequest } from "@/lib/types";
interface S{isAuthenticated:boolean;loading:boolean;error:string|null;login:(c:LoginRequest)=>Promise<boolean>;logout:()=>void;initialize:()=>void;}
export const useAuthStore=create<S>((set)=>({isAuthenticated:false,loading:false,error:null,initialize:()=>{const t=localStorage.getItem("access_token");set({isAuthenticated:!!t});},login:async(c)=>{set({loading:true,error:null});try{const t=await authApi.login(c);localStorage.setItem("access_token",t.access_token);localStorage.setItem("refresh_token",t.refresh_token);set({isAuthenticated:true,loading:false});return true;}catch(e){set({error:(e as Error).message,loading:false});return false;}},logout:()=>{localStorage.removeItem("access_token");localStorage.removeItem("refresh_token");set({isAuthenticated:false});window.location.href="/login";}}));
