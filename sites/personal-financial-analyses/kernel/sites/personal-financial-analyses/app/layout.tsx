import type {Metadata} from 'next';
export const metadata:Metadata={title:'Personal Financial Analyses',description:'个人金融分析终端：方法、市场与证据研究。'};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="zh-CN"><body>{children}</body></html>}
