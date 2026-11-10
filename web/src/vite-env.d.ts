/// <reference types="vite/client" />
declare module 'virtual:majlis-inline' {
  const data: { replay: string; audit: string | null; kb: string | null } | null;
  export default data;
}
declare const __MAJLIS_SINGLE__: boolean;
