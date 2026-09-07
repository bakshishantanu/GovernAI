const PHRASE = "Build agents fast";
const SEPARATOR = "✦";
const REPEATS = 8;

export function Marquee() {
  const group = (
    <span className="flex shrink-0 items-center">
      {Array.from({ length: REPEATS }).map((_, i) => (
        <span key={i} className="flex items-center">
          <span
            className={`landing-display px-6 text-4xl md:text-6xl ${
              i % 2 === 0 ? "text-[var(--l-cream)]" : "text-[var(--l-orange)]"
            }`}
          >
            {PHRASE}
          </span>
          <span className="text-2xl md:text-3xl text-[var(--l-teal-soft)]">
            {SEPARATOR}
          </span>
        </span>
      ))}
    </span>
  );

  return (
    <div className="relative bg-[var(--l-navy-deep)] py-10 md:py-14 overflow-hidden">
      <div className="landing-marquee-track flex -rotate-2">
        {group}
        <span aria-hidden="true" className="flex shrink-0 items-center">
          {group}
        </span>
      </div>
    </div>
  );
}
