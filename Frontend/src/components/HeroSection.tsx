"use client"

import Image from "next/image"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { InfiniteSlider } from "@/components/ui/infinite-slider"
import { ProgressiveBlur } from "@/components/ui/progressive-blur"
import LiteYouTube from "@/components/ui/video/LiteYouTube"

export default function HeroSection() {
  return (
    <div
      style={{
        background: "#ffffff",
        backgroundImage: "radial-gradient(circle at 1px 1px, rgba(0, 0, 0, 0.20) 1px, transparent 0)",
        backgroundSize: "20px 20px",
      }}
      className="overflow-x-hidden bg-white"
    >
      <section className="pb-16 pt-8 sm:pb-20 sm:pt-10 md:pb-32 lg:pb-56 lg:pt-[7.5rem] ">
        <div className="relative mx-auto grid grid-cols-1 md:grid-cols-2 max-w-7xl px-4 sm:px-6 items-center justify-center">
          <div className="mx-auto text-center md:text-start my-16 md:my-0 flex flex-col items-center md:items-start justify-center gap-8">
            <h1 className="text-4xl font-bold leading-[1] tracking-tight sm:text-5xl md:text-6xl lg:text-7xl">
              <span className="text-gray-900 bg-clip-text ">
                A Sounding <br /> Board for
              </span>
              <span className="block mt-3  text-brand-500    ">
                Early Stage <br /> African Entrepreneurs
              </span>
            </h1>

            <div className="flex flex-col items-center justify-center gap-4 sm:flex-row sm:justify-start">
              <div>
                <Link href="/choose-workspace">
                  <Button
                    size="lg"
                    className="w-full sm:w-auto px-8 py-6 text-base font-medium transition-all hover:scale-105"
                  >
                    Get Started
                  </Button>
                </Link>
              </div>

              <Button
                variant="outline"
                size="lg"
                className="w-full sm:w-auto px-8 py-6 text-base font-medium transition-all hover:bg-accent/50"
              >
                <Link href="#solutions">
                  See how it works
                </Link>
              </Button>
            </div>
          </div>

          <div>
            {/* YouTube Video Container with LiteYouTube for instant loading */}
            <div className="relative flex justify-center items-center min-h-[500px] overflow-visible">
              {/* Decorative Ring Background */}
              <div
                className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[555px] h-[555px] rounded-full pointer-events-none"
                style={{
                  background: `radial-gradient(circle, transparent 52%, #1a3a7a 53%, #244694 60%, #1a2d5a 100%)`,
                  zIndex: 1,
                  boxShadow: '0 0 30px rgba(36, 70, 148, 0.3)'
                }}
              />

              {/* YouTube Video Container with LiteYouTube for instant loading */}
              <div
                className="relative z-5 w-[700px] h-[350px] max-w-full rounded-xl overflow-hidden shadow-[0_20px_50px_rgba(18,138,163,0.2)] transform hover:scale-[1.01] transition-transform duration-300 border-2 border-white/20"
                style={{
                  aspectRatio: '16/9',
                }}
              >
                <LiteYouTube
                  videoId="SMeea4-H8vQ"
                  title="Yuba - A Sounding Board for African Entrepreneurs"
                  thumbnailQuality="maxresdefault"
                />
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="md:-mt-16 py-8 md:py-0 md:pb-16">
        <div className="group relative m-auto max-w-6xl px-4 sm:px-6">
          <div className="flex flex-col items-center md:flex-row">
            <div className="mb-4 md:mb-0 md:max-w-44 md:border-r md:pr-6">
              <p className="text-center text-md md:text-end font-medium tracking-tight text-brand-500">
                Trusted by early stage founders and ecosystem builders.
              </p>
            </div>

            <div className="relative py-6 md:w-[calc(100%-11rem)]">
              <InfiniteSlider speedOnHover={20} speed={40} gap={112}>
                <div className="flex">
                  <Image
                    className="mx-auto h-20 w-auto object-contain"
                    src='/assets/partners/microsoft-for-startups.png'
                    alt='Microsoft for Startups'
                    height={80}
                    width={240}
                  />
                </div>

                <div className="flex">
                  <Image
                    className="mx-auto h-16 w-auto object-contain"
                    src='/assets/partners/zero-one.png'
                    alt='Zero One'
                    height={64}
                    width={180}
                  />
                </div>

                <div className="flex">
                  <Image
                    className="mx-auto h-16 w-auto object-contain"
                    src='/assets/partners/Dossie Technologies.png'
                    alt='Dossie Technologies'
                    height={64}
                    width={180}
                  />
                </div>

                <div className="flex">
                  <Image
                    className="mx-auto h-20 w-auto object-contain"
                    src='/assets/partners/Weder-logo.png'
                    alt='Weder Logo'
                    height={80}
                    width={240}
                  />
                </div>

                <div className="flex">
                  <Image
                    className="mx-auto h-20 w-auto object-contain"
                    src='/assets/partners/microsoft-for-startups.png'
                    alt='Microsoft for Startups'
                    height={80}
                    width={240}
                  />
                </div>

                <div className="flex">
                  <Image
                    className="mx-auto h-16 w-auto object-contain"
                    src='/assets/partners/zero-one.png'
                    alt='Zero One'
                    height={64}
                    width={180}
                  />
                </div>

                <div className="flex">
                  <Image
                    className="mx-auto h-16 w-auto object-contain"
                    src='/assets/partners/Dossie Technologies.png'
                    alt='Dossie Technologies'
                    height={64}
                    width={180}
                  />
                </div>

                <div className="flex">
                  <Image
                    className="mx-auto h-20 w-auto object-contain"
                    src='/assets/partners/Weder-logo.png'
                    alt='Weder Logo'
                    height={80}
                    width={240}
                  />
                </div>
              </InfiniteSlider>

              <div className="bg-linear-to-r from-background absolute inset-y-0 left-0 w-20"></div>
              <div className="bg-linear-to-l from-background absolute inset-y-0 right-0 w-20"></div>
              <ProgressiveBlur
                className="pointer-events-none absolute left-0 top-0 h-full w-20"
                direction="left"
                blurIntensity={1}
              />
              <ProgressiveBlur
                className="pointer-events-none absolute right-0 top-0 h-full w-20"
                direction="right"
                blurIntensity={1}
              />
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}