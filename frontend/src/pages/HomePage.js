// HomePage.js

import React, { useState } from 'react';
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
  const [isUploading, setIsUploading] = useState(false);
  

  const handleFileChange = async (event) => {
    const file = event.target.files[0];
    if (file && file.type === 'application/pdf') {
      const formData = new FormData();
      formData.append('pdf_file', file);

      setIsUploading(true);
      
      try {
        const response = await fetch('http://localhost:5000/upload_pdf', {
          method: 'POST',
          body: formData,
        });

        const data = await response.json();

        if (response.ok) {
          console.log('Upload erfolgreich:', data);
          // ✅ HIER ANPASSEN: Übergebe pdf_id, filename und pdf_url
          navigate('/chat', { 
            state: { 
              pdfId: data.pdf_id, // Dies ist der unique_filename für die Backend-Kommunikation
              displayFileName: data.filename, // Dies ist der ursprüngliche Dateiname für die Anzeige
              pdfUrl: data.pdf_url // Die URL zum Anzeigen der PDF
            } 
          });
        } else {
          alert('Upload fehlgeschlagen: ' + data.error);
        }
      } catch (error) {
        alert('Fehler beim Upload: ' + error.message);
      } finally {
        setIsUploading(false);
      }
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
            disabled={isUploading}
          />

          <label htmlFor="pdf-upload" className={`upload-button ${isUploading ? 'disabled' : ''}`}>
            {isUploading ? 'Uploading...' : 'Choose File'}
          </label>

          {/* Spinner */}
          {isUploading && <div className="spinner" />}

          <br />
          <br />
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