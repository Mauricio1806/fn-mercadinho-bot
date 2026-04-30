import { BrowserRouter, Routes, Route, Navigate, Outlet } from "react-router-dom";
import { Sidebar } from "@/components/layout/Sidebar";
import { AuthGuard } from "@/components/layout/AuthGuard";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import Pedidos from "@/pages/Pedidos";
import Clientes from "@/pages/Clientes";
import Produtos from "@/pages/Produtos";
import Conversas from "@/pages/Conversas";
import Relatorios from "@/pages/Relatorios";
function Layout(){return(<AuthGuard><div className="flex min-h-screen bg-gray-50"><Sidebar/><main className="flex-1 pl-[240px]"><div className="max-w-7xl mx-auto px-6 py-8"><Outlet/></div></main></div></AuthGuard>);}
export default function App(){return(<BrowserRouter><Routes><Route path="/login" element={<Login/>}/><Route element={<Layout/>}><Route path="/" element={<Navigate to="/dashboard" replace/>}/><Route path="/dashboard" element={<Dashboard/>}/><Route path="/pedidos" element={<Pedidos/>}/><Route path="/clientes" element={<Clientes/>}/><Route path="/produtos" element={<Produtos/>}/><Route path="/conversas" element={<Conversas/>}/><Route path="/relatorios" element={<Relatorios/>}/></Route><Route path="*" element={<Navigate to="/dashboard" replace/>}/></Routes></BrowserRouter>);}
