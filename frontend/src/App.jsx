import { useEffect, useState } from "react";
import "./App.css";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

function App() {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const [formData, setFormData] = useState({
    city: "Austin",
    country: "USA",
    category: "dentist",
    limit: 10,
  });

  const loadLeads = async () => {
    try {
      const response = await fetch(`${API_URL}/api/leads`);
      const data = await response.json();
      setLeads(data);
    } catch (error) {
      setMessage("Unable to connect to the backend.");
      console.error(error);
    }
  };

  useEffect(() => {
    loadLeads();
  }, []);

  const handleChange = (event) => {
    setFormData({
      ...formData,
      [event.target.name]: event.target.value,
    });
  };

  const discoverLeads = async (event) => {
    event.preventDefault();

    setLoading(true);
    setMessage("Searching for businesses...");

    try {
      const response = await fetch(
        `${API_URL}/api/leads/discover`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            city: formData.city,
            country: formData.country,
            category: formData.category,
            limit: Number(formData.limit),
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Lead discovery failed");
      }

      setMessage(
        `Discovery complete: ${data.saved} saved, ${data.duplicates} duplicates.`
      );

      await loadLeads();
    } catch (error) {
      setMessage(`Error: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const generateOutreach = async (leadId) => {
    try {
      setMessage("Generating outreach email...");

      const response = await fetch(
        `${API_URL}/api/leads/${leadId}/outreach`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to generate outreach");
      }

      const email = data.outreach_email;

      alert(
        `Subject:\n${email.subject}\n\nMessage:\n${email.body}`
      );

      setMessage("Outreach email generated.");
    } catch (error) {
      setMessage(`Error: ${error.message}`);
    }
  };

  const enrichContact = async (leadId) => {
    try {
      setMessage("Searching for contact information...");

      const response = await fetch(
        `${API_URL}/api/leads/${leadId}/enrich-contact`,
        {
          method: "POST",
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Contact enrichment failed");
      }

      setMessage("Contact enrichment completed.");

      await loadLeads();
    } catch (error) {
      setMessage(`Error: ${error.message}`);
    }
  };

  const createGmailDraft = async (leadId) => {
    try {
      setMessage("Creating Gmail draft...");

      const response = await fetch(
        `${API_URL}/api/leads/${leadId}/gmail-draft`,
        {
          method: "POST",
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to create Gmail draft");
      }

      setMessage("Gmail draft created successfully.");
    } catch (error) {
      setMessage(`Error: ${error.message}`);
    }
  };

  const totalLeads = leads.length;

  const highPriorityLeads = leads.filter(
    (lead) =>
      lead.priority === "HIGH" ||
      lead.priority === "VERY_HIGH"
  ).length;

  const leadsWithEmail = leads.filter(
    (lead) => lead.email
  ).length;

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>Foreign Client Engine</h1>

          <p>
            Discover businesses, analyze opportunities, and automate outreach.
          </p>
        </div>

        <button
          className="secondary-btn"
          onClick={loadLeads}
        >
          Refresh Leads
        </button>
      </header>

      <main>
        <section className="search-card">
          <h2>Discover New Clients</h2>

          <form onSubmit={discoverLeads}>
            <div className="form-grid">
              <div className="input-group">
                <label>City</label>

                <input
                  type="text"
                  name="city"
                  value={formData.city}
                  onChange={handleChange}
                  placeholder="Austin"
                  required
                />
              </div>

              <div className="input-group">
                <label>Country</label>

                <input
                  type="text"
                  name="country"
                  value={formData.country}
                  onChange={handleChange}
                  placeholder="USA"
                  required
                />
              </div>

              <div className="input-group">
                <label>Business Category</label>

                <input
                  type="text"
                  name="category"
                  value={formData.category}
                  onChange={handleChange}
                  placeholder="Dentist"
                  required
                />
              </div>

              <div className="input-group">
                <label>Number of Leads</label>

                <input
                  type="number"
                  name="limit"
                  min="1"
                  max="50"
                  value={formData.limit}
                  onChange={handleChange}
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              className="primary-btn"
              disabled={loading}
            >
              {loading
                ? "Discovering..."
                : "Discover Businesses"}
            </button>
          </form>
        </section>

        {message && (
          <div className="message-box">
            {message}
          </div>
        )}

        <section className="stats">
          <div className="stat-card">
            <span>Total Leads</span>
            <strong>{totalLeads}</strong>
          </div>

          <div className="stat-card">
            <span>High Priority</span>
            <strong>{highPriorityLeads}</strong>
          </div>

          <div className="stat-card">
            <span>Emails Found</span>
            <strong>{leadsWithEmail}</strong>
          </div>
        </section>

        <section className="leads-section">
          <div className="section-title">
            <div>
              <h2>Client Leads</h2>

              <span>
                Manage discovered business opportunities.
              </span>
            </div>

            <span>{leads.length} leads</span>
          </div>

          {leads.length === 0 ? (
            <div className="empty-state">
              <h3>No leads found yet</h3>

              <p>
                Use the discovery form above to find
                potential foreign clients.
              </p>
            </div>
          ) : (
            <div className="leads-grid">
              {leads.map((lead) => (
                <div
                  className="lead-card"
                  key={lead.id}
                >
                  <div className="lead-top">
                    <h3>{lead.business_name}</h3>

                    <span
                      className={`priority ${lead.priority
                        ?.toLowerCase()
                        .replace("_", "-")}`}
                    >
                      {lead.priority}
                    </span>
                  </div>

                  <div className="lead-info">
                    <p>
                      <strong>Location:</strong>{" "}
                      {lead.city}, {lead.country}
                    </p>

                    <p>
                      <strong>Category:</strong>{" "}
                      {lead.category}
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
                      <strong>Recommended:</strong>{" "}
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
                      className="action-btn"
                      onClick={() =>
                        generateOutreach(lead.id)
                      }
                    >
                      Generate Email
                    </button>

                    <button
                      className="secondary-btn"
                      onClick={() =>
                        enrichContact(lead.id)
                      }
                    >
                      Find Contact
                    </button>

                    <button
                      className="gmail-btn"
                      disabled={!lead.email}
                      onClick={() =>
                        createGmailDraft(lead.id)
                      }
                    >
                      Gmail Draft
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;
