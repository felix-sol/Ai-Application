function Header({ id, title, className, children }) {
  return (
    <header id={id} className={className}>
      <h1>{title}</h1>
      {children}
    </header>
  );
}

export default Header;