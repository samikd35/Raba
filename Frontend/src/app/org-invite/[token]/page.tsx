import TokenRedirectClient from '../TokenRedirectClient';

interface Params {
  params: { token: string };
}

export default function TokenPage({ params }: { params: { token: string } }) {
  const token = params?.token ?? "";
  return <TokenRedirectClient token={token} />;
}
