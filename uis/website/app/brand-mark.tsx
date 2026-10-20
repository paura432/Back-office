export function BrandMark({ large = false }: { large?: boolean }) {
  return <span className={large ? 'brand-mark brand-mark--large' : 'brand-mark'} aria-hidden="true"><i></i><i></i><i></i></span>;
}
