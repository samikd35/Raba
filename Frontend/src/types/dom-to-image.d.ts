declare module 'dom-to-image' {
  interface Options {
    quality?: number;
    bgcolor?: string;
    width?: number;
    height?: number;
    style?: Record<string, any>;
    filter?: (node: any) => boolean;
    cacheBust?: boolean;
    pixelRatio?: number;
  }

  export function toPng(node: HTMLElement, options?: Options): Promise<string>;
  export function toJpeg(node: HTMLElement, options?: Options): Promise<string>;
  export function toSvg(node: HTMLElement, options?: Options): Promise<string>;
  export function toBlob(node: HTMLElement, options?: Options): Promise<Blob>;
}
