import { NextRequest, NextResponse } from 'next/server'

const BACKEND = process.env.BACKEND_URL ?? 'http://localhost:8000'
const API_KEY = process.env.BACKEND_API_KEY ?? ''

export async function POST(req: NextRequest, { params }: { params: Promise<{ id: string; eid: string }> }) {
  const { id, eid } = await params
  const body = await req.json()
  const res = await fetch(`${BACKEND}/api/v1/deals/${id}/escalations/${eid}/resolve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-API-Key': API_KEY },
    body: JSON.stringify(body),
  })
  return NextResponse.json(await res.json(), { status: res.status })
}
