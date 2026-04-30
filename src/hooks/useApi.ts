import { useCallback, useEffect, useState } from "react";
export function useApi<T>(fetcher:()=>Promise<T>,deps:unknown[]=[]) {
  const [data,setData]=useState<T|null>(null);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState<string|null>(null);
  const load=useCallback(async()=>{setLoading(true);setError(null);try{setData(await fetcher());}catch(e){setError((e as Error).message);}finally{setLoading(false);}},deps); // eslint-disable-line
  useEffect(()=>{load();},[load]);
  return {data,loading,error,reload:load};
}
export function usePolling<T>(fetcher:()=>Promise<T>,intervalMs=15000,deps:unknown[]=[]) {
  const r=useApi<T>(fetcher,deps);
  useEffect(()=>{const id=setInterval(r.reload,intervalMs);return()=>clearInterval(id);},[intervalMs]); // eslint-disable-line
  return r;
}
