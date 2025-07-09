/* Implements the Functionality of the first page of the frontend */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

/* Imports the relevant styling */
import './HomePage.css';
import Header from '../components/Header';
import headerStyles from '../components/Header.module.css';
import Footer from '../components/Footer';
import footerStyles from '../components/Footer.module.css';
import Card from '../components/Card';
import cardStyles from '../components/Card.module.css';

/* main entry point for the first page of the application */
function HomePage() {
  const navigate = useNavigate(); // hook from react-router-dom to navigate to other pages
  const [isUploading, setIsUploading] = useState(false); // State to manage the upload status
  
  /* input of file activates this function and gives the pdf file to the backend at shown URL, then navigates to ChatPage.js  */
  const handleFileChange = async (event) => {
    const file = event.target.files[0];
    if (file && file.type === 'application/pdf') {
      const formData = new FormData();
      formData.append('pdf_file', file); // 'pdf_file' is the key expected by the backend

      setIsUploading(true);
      
      try {
        const response = await fetch('http://localhost:5000/upload_pdf', {  // URL from the backend to upload the PDF file 
          method: 'POST',
          body: formData,
        });

        const data = await response.json();

        if (response.ok) {
          console.log('Upload erfolgreich:', data);
          navigate('/chat', {
            state: {
              pdfId: data.pdf_id,                   
              displayFileName: data.filename,  // Filename of input PDF shown in Frontend to display on ChatPage.js
              pdfUrl: data.pdf_url,                
              jsonUrl: data.json_url                
            }
        });

        } else {
          alert('Upload failed: ' + data.error);
        }
      } catch (error) {
        alert('Error during upload: ' + error.message);
      } finally {
        setIsUploading(false);
      }
    } else {
      alert('Please select a valid PDF file .');
    }
  };


 /* Render the HomePage, mainly contains all the visible Elements displayed on the HomePage.js */
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

          {/* Spinner for loading animation */}
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