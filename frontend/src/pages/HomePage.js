
import React from 'react';
import { useNavigate } from 'react-router-dom';
import './HomePage.css';
import Header from '../components/Header';
import headerStyles from '../components/Header.module.css';
import Footer from '../components/Footer';
import footerStyles from '../components/Footer.module.css';
import Card from '../components/Card';
import cardStyles from '../components/Card.module.css';



function HomePage() {
  const navigate = useNavigate();
 
  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (file && file.type === 'application/pdf') {
      const fileName = file.name;
      console.log('PDF ausgewählt:', fileName);

      
      navigate('/chat', { state: { pdfName: fileName } });

    } else {
      alert('Bitte wählen Sie eine gültige PDF-Datei aus.');
    }
  };

return (
  <>
   <Header
    title="Welcome to the PDF Chat"
    className={headerStyles.header}
  />


    <main className="home-container">
      <div className="content-box">
        <h1>Chat-Assistant</h1>
        <p>Upload your file and start chatting with it</p>

        <input
          type="file"
          id="pdf-upload"
          accept=".pdf"
          onChange={handleFileChange}
          style={{ display: 'none' }}
        />

        <label htmlFor="pdf-upload" className="upload-button">
          choose file
        </label>
        <br></br>
         <br></br>
        <p className="upload-instruction">
          make sure to upload a PDF file
        </p>

      </div>

      <Card 
  className={cardStyles.card} 
  imgClassName={cardStyles.cardImage} 
  title="Team Rocket"
>
  <p>
    The whole application is created, maintained and managed by <br />
    <strong className={cardStyles.names}>
      Bent Mildner <br />
      Marcel Seibt <br />
      Felix Soltau <br />
    </strong>
  </p>
</Card>
    </main>

    <Footer
  className={footerStyles.footer}
  title="Any Problems? Feel free to send us an E-Mail!"
  contact="felix.soltau@stud.leuphana.de"
/>
  </>
);

}
export default HomePage;