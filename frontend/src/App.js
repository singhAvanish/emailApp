import React, { useState, useEffect } from 'react';
import 'bootstrap/dist/css/bootstrap.min.css';

function App() {
  const [recipientEmails, setRecipientEmails] = useState('');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [pdfFile, setPdfFile] = useState(null);
  const [message, setMessage] = useState('');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  
  // Function to initiate OAuth2 authentication
  const handleAuth = () => {
    window.location.href = 'https://emailapp-rg19.onrender.com/auth';
  };
  
  // Function to handle email submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!isAuthenticated) {
      setMessage('Please authenticate with Google first.');
      return;
    }
    if (!pdfFile) {
      setMessage('Please select a PDF file.');
      return;
    }
    
    const reader = new FileReader();
    reader.readAsDataURL(pdfFile);
    reader.onload = async () => {
      const pdfBase64 = reader.result.split(',')[1];
      const data = {
        recipient_emails: recipientEmails.split(',').map(email => email.trim()),
        subject,
        body,
        pdf_file_base64: pdfBase64,
        pdf_file_name: pdfFile.name,
      };
      
      try {
        const response = await fetch('https://emailapp-rg19.onrender.com/send-email', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(data),
        });
        const result = await response.json();
        if (response.ok) {
          setMessage(result.message);
        } else {
          setMessage(result.error);
        }
      } catch (error) {
        console.error('Error sending email:', error);
        setMessage('Failed to send emails.');
      }
    };
  };
  
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('code')) {
      setIsAuthenticated(true);
      setMessage('Authentication successful! You can now send emails.');
    }
  }, []);
  
  return (
    <div className="container mt-5">
      <div className="row justify-content-center">
        <div className="col-md-8">
          <div className="card shadow-lg border-0">
            <div className="card-header bg-primary text-white text-center">
              <h2>Send Email</h2>
            </div>
            <div className="card-body">
              {!isAuthenticated ? (
                <div className="text-center">
                  <button className="btn btn-success btn-lg" onClick={handleAuth}>
                    Authenticate with Google
                  </button>
                </div>
              ) : (
                <form onSubmit={handleSubmit}>
                  <div className="mb-3">
                    <label className="form-label">Recipient Emails (comma-separated):</label>
                    <input
                      type="text"
                      className="form-control"
                      value={recipientEmails}
                      onChange={(e) => setRecipientEmails(e.target.value)}
                      required
                    />
                  </div>
                  <div className="mb-3">
                    <label className="form-label">Subject:</label>
                    <input
                      type="text"
                      className="form-control"
                      value={subject}
                      onChange={(e) => setSubject(e.target.value)}
                      required
                    />
                  </div>
                  <div className="mb-3">
                    <label className="form-label">Body:</label>
                    <textarea
                      className="form-control"
                      rows="5"
                      value={body}
                      onChange={(e) => setBody(e.target.value)}
                      required
                    />
                  </div>
                  <div className="mb-3">
                    <label className="form-label">Attach PDF:</label>
                    <input
                      type="file"
                      className="form-control"
                      accept="application/pdf"
                      onChange={(e) => setPdfFile(e.target.files[0])}
                      required
                    />
                  </div>
                  <div className="d-grid">
                    <button type="submit" className="btn btn-primary btn-lg">
                      Send Email
                    </button>
                  </div>
                </form>
              )}
              {message && <div className="mt-3 alert alert-info">{message}</div>}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
