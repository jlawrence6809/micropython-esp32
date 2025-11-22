type SectionProps = {
  className?: string;
  title: string;
  children: any;
};

/**
 * A section of the page that can be used to group related content.
 */
export const Section = ({ className = '', title, children }: SectionProps) => {
  return (
    <div className={`Section ${className}`}>
      <h2>{title}</h2>
      {children}
    </div>
  );
};
