
import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import './ChatPage.css';
import Header from '../components/Header';
import chatPageHeaderStyles from '../components/Header.module.css';
import Footer from '../components/Footer';
import chatPageFooterStyles from '../components/Footer.module.css';


function ChatPage() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');

  // HIER DIE ÄNDERUNG: Den übergebenen State auslesen
  const location = useLocation();
  // Wir lesen den pdfName aus dem State. Falls die Seite direkt aufgerufen wird,
  // nutzen wir einen Standardtext als Rückfalloption.
  const pdfName = location.state?.pdfName || 'PDF-Chat';

  const handleSendMessage = (e) => {
    e.preventDefault();
    if (input.trim() === '') return;

    const userMessage = { text: input, sender: 'user' };
    setMessages(prev => [...prev, userMessage]);

    setTimeout(() => {
      const botResponse = { text: `Antwort auf: "${input}"`, sender: 'bot' };
      setMessages(prev => [...prev, botResponse]);
    }, 1000);

    setInput('');
  };

  const handleExtractAndDownload = () => {
    const jsonResult = {
        "name_of_the_doc": pdfName,
       "CO2" : "…", 
       "NOX" : "…", 
       "Number_of_Electric_Vehicles" : "…", 
       "Impact" : "…", 
       "Risks" : "…", 
       "Opportunities" : "…", 
       "Strategy" : "…", 
       "Actions" : "…", 
       "Adopted_policies" : "…",
       "Targets" : "…" 
    };
    
    const jsonString = `data:text/json;charset=utf-8,${encodeURIComponent(
      JSON.stringify(jsonResult, null, 2)
    )}`;
    const link = document.createElement('a');
    link.href = jsonString;
    link.download = `${pdfName.split('.')[0]}-analyse.json`; 
    link.click();
  };

  return (
    <>
      <Header
  title="PDF-Chat"
  className={chatPageHeaderStyles.chatPageHeader}
>
  <Link to="/" className="back-button">Back to Main</Link>
</Header>

      <main className="chat-main">
        <div className="chat-window">
          <h2 id="h2"> {pdfName} </h2>
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
            placeholder="ask something..."
          />
          <button type="submit">Send</button>
          <button onClick={handleExtractAndDownload} className="download-button">
         Download
       </button>
        </form>
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