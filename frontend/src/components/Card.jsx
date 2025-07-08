
/* reusable component for the card, always comes with an image and h2 title and possible children content */
import cover from '../assets/rocket.jpg';

function Card({ className, imgClassName, title, children }) {
  return (
    <div className={className}>
      <img className={imgClassName} src={cover} alt="cover" />
      <h2>{title}</h2>
      {children}
    </div>
  );
}

export default Card;
