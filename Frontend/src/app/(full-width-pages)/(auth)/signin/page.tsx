'use client';

import { Suspense } from 'react';
import SignInForm from "@/components/auth/SignInForm";
import { useSearchParams } from 'next/navigation';

function SignInContent() {
  const searchParams = useSearchParams();
  const vbToken = searchParams.get('vb_token');
  const redirect = searchParams.get('redirect');

  return <SignInForm vbInvitationToken={vbToken} redirectUrl={redirect} />;
}

export default function SignIn() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <SignInContent />
    </Suspense>
  );
}
