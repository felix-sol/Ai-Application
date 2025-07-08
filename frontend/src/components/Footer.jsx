/* reusable component for the Footer with title, paragraph, children placeholder to add possible additions */

function Footer({ id, className, title, contact, children }) {
  return (
    <footer id={id} className={className}>
      <h4>{title}</h4>
      <p>Contact: <a href={`mailto:${contact}`}>{contact}</a></p>

      {children} {/* Optionaler Zusatz-Inhalt */} 
    </footer>
  );
}

export default Footer;
