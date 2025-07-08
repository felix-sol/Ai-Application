/* Implements the Functionality of the second page of the frontend */

import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Worker, Viewer } from '@react-pdf-viewer/core';
import '@react-pdf-viewer/core/lib/styles/index.css';

/* Imports the relevant styling */
import './ChatPage.css';
import Header from '../components/Header';
import chatPageHeaderStyles from '../components/Header.module.css';
import Footer from '../components/Footer';
import chatPageFooterStyles from '../components/Footer.module.css';


function ChatPage() {
  // State to manage chat messages, input field, and loading state
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const location = useLocation();
  const pdfId = location.state?.pdfId || 'PDF-Chat'; //  unique_filename
  const displayFileName = location.state?.displayFileName || 'Unbekanntes Dokument'; // original file name of uploaded pdf
  const pdfUrl = location.state?.pdfUrl || null; //  URL to PDF

  // Handles input messages and sends them to the backend
  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (input.trim() === '' || isLoading) return;

    const userMessage = { text: input, sender: 'user' };
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    // Send the input message to chat endpoint
    try {
      const response = await fetch('http://localhost:5000/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: input,
          pdf_id: pdfId, 
        }),
      });

      const data = await response.json();

      const botResponse = {
        text: response.ok ? data.answer : data.error || "Fehler beim Chatten.",
        sender: 'bot',
      };
      setMessages(prev => [...prev, botResponse]);
    } catch (error) {
      const botResponse = { text: 'Netzwerkfehler: ' + error.message, sender: 'bot' };
      setMessages(prev => [...prev, botResponse]);
    } finally {
      setIsLoading(false);
      setInput('');
    }
  };

  const handleExtractAndDownload = () => {
    const jsonResult = {
      "name_of_the_doc": displayFileName, 
      "CO2": "…",
      "NOX": "…",
      "Number_of_Electric_Vehicles": "…",
      "Impact": "…",
      "Risks": "…",
      "Opportunities": "…",
      "Strategy": "…",
      "Actions": "…",
      "Adopted_policies": "…",
      "Targets": "…"
    };

    const jsonString = `data:text/json;charset=utf-8,${encodeURIComponent(
      JSON.stringify(jsonResult, null, 2)
    )}`;
    const link = document.createElement('a');
    link.href = jsonString;
    // Der Dateiname für den Download sollte vom ursprünglichen Dateinamen abgeleitet werden.
    // Das ".split('.')[0]" ist nicht ganz robust bei Dateinamen mit mehreren Punkten.
    // Besser wäre es, die Dateiendung korrekt zu entfernen:
    const downloadFileNameWithoutExtension = displayFileName.split('.').slice(0, -1).join('.');
    link.download = `${downloadFileNameWithoutExtension}-analyse.json`;
    link.click();
  };

  /* Render the ChatPage, mainly contains all the visible Elements displayed on the ChatPage.js */
  return (
    <>
      <Header
        title="PDF-Chat"
        className={chatPageHeaderStyles.chatPageHeader}>
        <Link to="/" className="back-button">Return to Main</Link>
      </Header>

      <main className="chat-main">
        {/* PDF-Viewer */}
        <div className="pdf-viewer">
          <Worker workerUrl={`https://unpkg.com/pdfjs-dist@3.11.174/build/pdf.worker.min.js`}>
            {pdfUrl ? (
              <Viewer fileUrl={pdfUrl} />
            ) : (
              <div className="pdf-viewer-placeholder">
                <p>Could not load document or PDF is not available.</p>
              </div>
            )}
          </Worker>
        </div>

        {/* Chat-Bereich */}
        <div className="chat-container">
          <div className="chat-window">
            <h2 id="h2">{displayFileName}</h2> 

            {messages.map((msg, index) => (
              <div key={index} className={`message ${msg.sender}`}>
                <p>{msg.text}</p>
              </div>
            ))}
          </div>

          <form className="chat-input-area" onSubmit={handleSendMessage}>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey && !isLoading) {
                  e.preventDefault();
                  handleSendMessage(e);
                }
              }}
              placeholder="ask something..."
              disabled={isLoading}
            />
            <button type="submit" disabled={isLoading}>Send</button>
            <button type="button" onClick={handleExtractAndDownload} disabled={isLoading}>
              Download Key Values
            </button>
          </form>
        </div>
      </main>

      <Footer
        className={chatPageFooterStyles.chatPageFooter}
        title="Any Problems? Feel free to send us an E-Mail!"
        contact="felix.soltau@stud.leuphana.de"
      />
    </>
  );
}

export default ChatPage;