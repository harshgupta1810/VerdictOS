import { NextRequest, NextResponse } from 'next/server'

const BACKEND = process.env.BACKEND_URL ?? 'http://localhost:8000'
const API_KEY = process.env.BACKEND_API_KEY ?? ''

export async function POST(req: NextRequest) {
  const form = await req.formData()
  const res = await fetch(`${BACKEND}/api/v1/upload`, {
    method: 'POST',
    headers: { 'X-API-Key': API_KEY },
    body: form,
  })
  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}
