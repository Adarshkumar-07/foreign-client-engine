import { useEffect, useState } from "react";
import axios from "axios";
import "./App.css";

const API_URL = "http://localhost:8000";

function App() {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedLead, setSelectedLead] = useState(null);

  const [city, setCity] = useState("Austin");
  const [country, setCountry] = useState("USA");
  const [category, setCategory] = useState("dentist");

  const loadLeads = async () => {
    try {
      setLoading(true);

      const response = await axios.get(`${API_URL}/api/leads`);

      setLeads(response.data);
    } catch (error) {
      console.error("Error loading leads:", error);
      alert("Could not connect to the backend.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLeads();
  }, []);

  const discoverLeads = async () => {
    try {
      setLoading(true);

      const response = await axios.post(
        `${API_URL}/api/leads/discover`,
        {
          city,
          country,
          category,
        }
      );

      alert(
        `Discovery complete!\nFound: ${response.data.total_discovered}\nSaved: ${response.data.saved}`
      );

      loadLeads();
    } catch (error) {
      console.error(error);
      alert("Lead discovery failed.");
    } finally {
      setLoading(false);
    }
  };

  const enrichLead = async (leadId) => {
    try {
      setLoading(true);

      const response = await axios.post(
        `${API_URL}/api/leads/${leadId}/enrich-contact`
      );

      alert(
        `Contact enrichment complete!\nEmail: ${
          response.data.contact_enrichment?.email || "Not found"
        }\nPhone: ${
          response.data.contact_enrichment?.phone || "Not found"
        }`
      );

      loadLeads();
    } catch (error) {
      console.error(error);
      alert("Contact enrichment failed.");
    } finally {
      setLoading(false);
    }
  };

  const generateEmail = async (leadId) => {
    try {
      setLoading(true);

      const response = await axios.post(
        `${API_URL}/api/leads/${leadId}/gmail-draft`
      );

      setSelectedLead(response.data);
    } catch (error) {
      console.error(error);
      alert("Email generation failed.");
    } finally {
      setLoading(false);
    }
  };

  const highPriorityLeads = leads.filter(
    (lead) => lead.priority === "HIGH"
  );

  const mediumPriorityLeads = leads.filter(
    (lead) => lead.priority === "MEDIUM"
  );

  const leadsWithContact = leads.filter(
    (lead) => lead.email || lead.phone
  );

  return (
    <div className="app">
      <header>
        <div>
          <h1>Foreign Client Engine</h1>
          <p>Find, analyze and contact potential international clients.</p>
        </div>

        <button onClick={loadLeads}>
          Refresh Leads
        </button>
      </header>

      <section className="stats">
        <div className="stat-card">
          <h3>Total Leads</h3>
          <span>{leads.length}</span>
        </div>

        <div className="stat-card">
          <h3>High Priority</h3>
          <span>{highPriorityLeads.length}</span>
        </div>

        <div className="stat-card">
          <h3>Medium Priority</h3>
          <span>{mediumPriorityLeads.length}</span>
        </div>

        <div className="stat-card">
          <h3>Contacts Found</h3>
          <span>{leadsWithContact.length}</span>
        </div>
      </section>

      <section className="discovery">
        <h2>Discover New Clients</h2>

        <div className="form-row">
          <input
            type="text"
            value={city}
            placeholder="City"
            onChange={(e) => setCity(e.target.value)}
          />

          <input
            type="text"
            value={country}
            placeholder="Country"
            onChange={(e) => setCountry(e.target.value)}
          />

          <input
            type="text"
            value={category}
            placeholder="Business Category"
            onChange={(e) => setCategory(e.target.value)}
          />

          <button
            onClick={discoverLeads}
            disabled={loading}
          >
            Discover Leads
          </button>
        </div>
      </section>

      <section className="leads-section">
        <div className="section-title">
          <h2>Business Leads</h2>

          {loading && <span>Loading...</span>}
        </div>

        <div className="lead-grid">
          {leads.map((lead) => (
            <div className="lead-card" key={lead.id}>
              <div className="lead-header">
                <h3>{lead.business_name}</h3>

                <span
                  className={`priority ${lead.priority?.toLowerCase()}`}
                >
                  {lead.priority}
                </span>
              </div>

              <p className="location">
                📍 {lead.city}, {lead.country}
              </p>

              <div className="lead-info">
                <p>
                  <strong>Category:</strong> {lead.category}
                </p>

                <p>
                  <strong>Website:</strong>{" "}
                  {lead.website_status}
                </p>

                <p>
                  <strong>Score:</strong>{" "}
                  {lead.lead_score}
                </p>

                <p>
                  <strong>Service:</strong>{" "}
                  {lead.recommended_service}
                </p>

                <p>
                  <strong>Email:</strong>{" "}
                  {lead.email || "Not found"}
                </p>

                <p>
                  <strong>Phone:</strong>{" "}
                  {lead.phone || "Not found"}
                </p>
              </div>

              <div className="actions">
                <button
                  onClick={() => enrichLead(lead.id)}
                  disabled={loading}
                >
                  Find Contact
                </button>

                <button
                  onClick={() => generateEmail(lead.id)}
                  disabled={loading}
                >
                  Generate Email
                </button>
              </div>
            </div>
          ))}
        </div>

        {!loading && leads.length === 0 && (
          <div className="empty">
            No leads found. Discover your first businesses.
          </div>
        )}
      </section>

      {selectedLead && (
        <div className="modal-overlay">
          <div className="email-modal">
            <button
              className="close"
              onClick={() => setSelectedLead(null)}
            >
              ×
            </button>

            <h2>Email Draft</h2>

            <h3>
              {selectedLead.business_name}
            </h3>

            {selectedLead.subject && (
              <p>
                <strong>Subject:</strong>{" "}
                {selectedLead.subject}
              </p>
            )}

            <pre>
              {selectedLead.body ||
                JSON.stringify(selectedLead, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
