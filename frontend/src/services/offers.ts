import { api } from './api'

export type OfferStatus = 'DRAFT' | 'ISSUED' | 'ACCEPTED' | 'DECLINED' | 'EXPIRED'
export interface OfferRecord {
  id: number; application_id: number; student_id: number; candidate_name: string; candidate_email: string
  company_id: number; company_name: string; job_drive_id: number; job_title: string; salary: number | null
  currency: string; joining_date: string | null; status: OfferStatus; offer_letter_reference: string | null
  issued_at: string | null; expires_at: string | null; created_at: string; updated_at: string
}
export async function fetchOffers() { return (await api.get<OfferRecord[]>('/api/offers')).data }
export async function createOffer(input: { application_id: number; salary: number; joining_date: string; expires_at?: string; offer_letter_reference?: string }) { return (await api.post<OfferRecord>('/api/offers', input)).data }
export async function issueOffer(id: number) { return (await api.post<OfferRecord>(`/api/offers/${id}/issue`)).data }
export async function updateOfferStatus(id: number, status: 'EXPIRED') { return (await api.patch<OfferRecord>(`/api/offers/${id}/status`, { status })).data }
export async function respondToOffer(id: number, status: 'ACCEPTED' | 'DECLINED') { return (await api.post<OfferRecord>(`/api/offers/${id}/respond`, { status })).data }
