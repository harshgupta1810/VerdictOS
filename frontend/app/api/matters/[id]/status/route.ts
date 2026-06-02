import { NextRequest, NextResponse } from 'next/server'

const BACKEND = process.env.BACKEND_URL ?? 'http://localhost:8000'
const API_KEY = process.env.BACKEND_API_KEY ?? ''

export async function GET(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const res = await fetch(`${BACKEND}/api/v1/deals/${id}/status`, { headers: { 'X-API-Key': API_KEY } })
  return NextResponse.json(await res.json(), { status: res.status })
}
