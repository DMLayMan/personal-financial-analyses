import {cloud} from '../../../lib/cloud';
export const dynamic='force-dynamic';
export async function GET(request:Request,{params}:any){return cloud(request,(await params).path);}
export async function POST(request:Request,{params}:any){return cloud(request,(await params).path);}
export async function PUT(request:Request,{params}:any){return cloud(request,(await params).path);}
