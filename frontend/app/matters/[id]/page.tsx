import { redirect } from 'next/navigation'

export default async function MatterIndexPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  redirect(`/matters/${id}/status`)
}
