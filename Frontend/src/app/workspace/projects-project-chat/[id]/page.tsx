'use client';

import React from 'react';
import { useParams, useRouter } from 'next/navigation';

// Components
import PageBreadcrumb from '@/components/common/PageBreadCrumb';
import ProjectChatView from '@/components/chat/ProjectChatView';

export default function ProjectChatPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params?.id as string;

  const handleBack = () => {
    router.push('/workspace/projects-project-chat');
  };

  return (
    <div className="flex flex-col h-[calc(100vh-100px)] overflow-hidden">
      <PageBreadcrumb pageTitle="Project Chat" />
      <ProjectChatView
        projectId={projectId}
        onBack={handleBack}
      />
    </div>
  );
}