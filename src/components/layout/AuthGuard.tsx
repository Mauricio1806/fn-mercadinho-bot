import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "@/stores/auth";
export function AuthGuard({children}:{children:React.ReactNode}){const{isAuthenticated,initialize}=useAuthStore();const navigate=useNavigate();useEffect(()=>{initialize();},[initialize]);useEffect(()=>{if(!isAuthenticated&&!localStorage.getItem("access_token"))navigate("/login");},[isAuthenticated,navigate]);if(!isAuthenticated&&!localStorage.getItem("access_token"))return null;return <>{children}</>;}
