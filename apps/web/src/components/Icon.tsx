export function Icon({
  name,
  className = "",
  title,
}: {
  name: string;
  className?: string;
  title?: string;
}) {
  return (
    <span aria-hidden={title ? undefined : true} className={`material-symbols-rounded ${className}`} title={title}>
      {name}
    </span>
  );
}
