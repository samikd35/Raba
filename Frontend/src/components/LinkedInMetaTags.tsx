import Head from 'next/head';

interface LinkedInMetaTagsProps {
  title?: string;
  description?: string;
  imageUrl?: string;
  url?: string;
  siteName?: string;
}

const LinkedInMetaTags: React.FC<LinkedInMetaTagsProps> = ({
  title = "Yuba - A Sounding Board for African Entrepreneurs",
  description = "Get contextual and actionable market insights to validate your business ideas. Join early-stage founders building the next generation of African startups.",
  imageUrl = "/images/og-image.png",
  url = "https://yuba.app",
  siteName = "Yuba"
}) => {
  return (
    <Head>
      {/* Primary Meta Tags */}
      <title>{title}</title>
      <meta name="title" content={title} />
      <meta name="description" content={description} />

      {/* Open Graph / Facebook / LinkedIn */}
      <meta property="og:type" content="website" />
      <meta property="og:url" content={url} />
      <meta property="og:title" content={title} />
      <meta property="og:description" content={description} />
      <meta property="og:image" content={imageUrl} />
      <meta property="og:image:width" content="1200" />
      <meta property="og:image:height" content="630" />
      <meta property="og:site_name" content={siteName} />
      <meta property="og:locale" content="en_US" />

      {/* Twitter */}
      <meta property="twitter:card" content="summary_large_image" />
      <meta property="twitter:url" content={url} />
      <meta property="twitter:title" content={title} />
      <meta property="twitter:description" content={description} />
      <meta property="twitter:image" content={imageUrl} />

      {/* Additional LinkedIn-specific tags */}
      <meta name="author" content="Yuba" />
      <meta name="robots" content="index, follow" />
    </Head>
  );
};

export default LinkedInMetaTags;
