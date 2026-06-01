import { NextRequest, NextResponse } from 'next/server'

const BACKEND = process.env.BACKEND_URL ?? 'http://localhost:8000'
const API_KEY = process.env.BACKEND_API_KEY ?? ''

export async function POST(req: NextRequest) {
  const body = await req.json()
  const res = await fetch(`${BACKEND}/api/v1/deals`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-API-Key': API_KEY },
    body: JSON.stringify(body),
  })
  return NextResponse.json(await res.json(), { status: res.status })
}

export async function GET() {
  const res = await fetch(`${BACKEND}/api/v1/deals`, {
    headers: { 'X-API-Key': API_KEY },
  })
  return NextResponse.json(await res.json(), { status: res.status })
}
