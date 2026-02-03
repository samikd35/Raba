'use client';

import { use } from 'react';
import VBSessionDetail from '@/components/venture-builder/sessions/VBSessionDetail';

interface SessionDetailPageProps {
  params: Promise<{ session_id: string }>;
}

export default function SessionDetailPage({ params }: SessionDetailPageProps) {
  const { session_id } = use(params);
  return <VBSessionDetail sessionId={session_id} />;
}
