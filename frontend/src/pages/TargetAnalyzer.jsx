import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';
import './TargetAnalyzer.css';

function TargetAnalyzer() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [target, setTarget] = useState('RIPK2');
  const [indication, setIndication] = useState('Ulcerative Colitis');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const handleAnalyze = async (e) => {
    e.preventDefault();
    if (!target || !indication) return;

    setLoading(true);
    setError(null);
    setData(null);

    try {
      const token = localStorage.getItem('authToken');
      const response = await axios.post(
        '/api/target-analyzer/analyze',
        {
          target: target.trim(),
          indication: indication.trim()
        },
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );

      setData(response.data);
    } catch (err) {
      console.error('Analysis error:', err);
      setError(err.response?.data?.detail || 'Failed to generate analysis. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const renderSection = (title, content) => (
    <div className="section-card">
      <h3>{title}</h3>
      <div className="section-content">{content}</div>
    </div>
  );

  return (
    <div className="target-analyzer-container">
      {/* Main Content */}
      <main className="ta-main">
        <div className="ta-header-section">
          <button className="back-button" onClick={() => navigate('/')}>
            ← Back to Home
          </button>
          <div className="ta-title-block">
            <div className="ta-icon-wrapper">
              <span className="ta-icon">🧬</span>
            </div>
            <h1>Target Analyzer</h1>
            <p className="ta-subtitle">AI-powered drug target and indication analysis</p>
          </div>
        </div>
        {!data && !loading ? (
          <div className="ta-input-section">
            <div className="ta-intro">
              <h2>Accelerate Your Drug Discovery Research</h2>
              <p>Generate comprehensive deep-dive reports on any drug target and indication pair in seconds using advanced AI.</p>
            </div>

            <div className="ta-form-card">
              <form onSubmit={handleAnalyze} className="ta-form">
                <div className="form-row">
                  <div className="form-group">
                    <label>Target Molecule</label>
                    <input
                      type="text"
                      value={target}
                      onChange={(e) => setTarget(e.target.value)}
                      placeholder="e.g. RIPK2, JAK1"
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label>Indication / Disease</label>
                    <input
                      type="text"
                      value={indication}
                      onChange={(e) => setIndication(e.target.value)}
                      placeholder="e.g. Ulcerative Colitis"
                      required
                    />
                  </div>
                </div>
                <button type="submit" className="analyze-btn">
                  🔬 Start Deep Analysis
                </button>
              </form>
            </div>

            <div className="ta-features">
              <div className="feature-item">
                <h3>Competitive Landscape</h3>
                <p>Real-time trial data & competitors</p>
              </div>
              <div className="feature-item">
                <h3>Risk Assessment</h3>
                <p>Clinical, technical & safety scoring</p>
              </div>
              <div className="feature-item">
                <h3>Strategic Insights</h3>
                <p>Differentiation & unmet needs</p>
              </div>
            </div>
          </div>
        ) : loading ? (
          <div className="ta-loading">
            <div className="spinner"></div>
            <h2>Analyzing Target Potential</h2>
            <p>Scouring databases for {target} in {indication}...</p>
            <div className="loading-tags">
              <span>Clinical Trials</span>
              <span>•</span>
              <span>Patents</span>
              <span>•</span>
              <span>Biological Mechanisms</span>
            </div>
          </div>
        ) : error ? (
          <div className="ta-error">
            <div className="error-icon">⚠️</div>
            <h3>Analysis Failed</h3>
            <p>{error}</p>
            <button onClick={() => setError(null)}>Try Again</button>
          </div>
        ) : data ? (
          <div className="ta-results">
            <div className="results-header">
              <h1>
                {data.target} <span className="for-text">for</span> {data.indication}
              </h1>
              <button className="new-analysis-btn" onClick={() => setData(null)}>
                New Analysis
              </button>
            </div>

            <div className="results-content">
              {/* Biological Overview */}
              {renderSection(
                '1. Biological Overview',
                <div className="bio-overview">
                  <div className="subsection">
                    <h4>Structural Domains</h4>
                    <div className="domains-list">
                      {data.biological_overview.structural_domains.map((domain, i) => (
                        <div key={i} className="domain-item">
                          <strong>{domain.name}:</strong> {domain.description}
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="subsection">
                    <h4>Mechanism of Action</h4>
                    <div className="mechanism-content">
                      <ol className="mechanism-list">
                        {data.biological_overview.mechanistic_insights.map((insight, i) => (
                          <li key={i}>{insight}</li>
                        ))}
                      </ol>
                      {data.biological_overview.mechanism_image ? (
                        <div className="mechanism-image">
                          <img
                            src={data.biological_overview.mechanism_image}
                            alt="Mechanism of Action Diagram"
                            className="mechanism-diagram"
                          />
                          <p className="image-caption">
                            <span className="image-icon">🖼️</span> AI-generated schematic
                          </p>
                        </div>
                      ) : (
                        <div className="mechanism-placeholder">
                          <span className="placeholder-icon">🖼️</span>
                          <p>Diagram not available</p>
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="subsection-grid">
                    <div>
                      <h4>Human Validation</h4>
                      <p>{data.biological_overview.human_validation}</p>
                    </div>
                    <div>
                      <h4>Species Conservation</h4>
                      <p>{data.biological_overview.species_conservation}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Therapeutic Rationale */}
              {renderSection(
                '2. Therapeutic Rationale',
                <div className="rationale-grid">
                  <div className="rationale-box blue">
                    <h4>Pathway Positioning</h4>
                    <p>{data.therapeutic_rationale.pathway_positioning}</p>
                  </div>
                  <div className="rationale-box indigo">
                    <h4>Specificity vs Breadth</h4>
                    <p>{data.therapeutic_rationale.specificity_vs_breadth}</p>
                  </div>
                  <div className="rationale-box violet">
                    <h4>Modality Comparison</h4>
                    <p>{data.therapeutic_rationale.modality_comparison}</p>
                  </div>
                </div>
              )}

              {/* Pre-clinical Evidence */}
              {renderSection(
                '3. Pre-clinical Evidence',
                <div className="evidence-section">
                  <div className="subsection">
                    <h4>Human Genetic Evidence</h4>
                    <div style={{ marginBottom: '1rem' }}>
                      <strong>Monogenic Gain-of-Function Mutations:</strong>
                      <table className="evidence-table" style={{ marginTop: '0.5rem' }}>
                        <thead>
                          <tr>
                            <th>Variant</th>
                            <th>Phenotype</th>
                          </tr>
                        </thead>
                        <tbody>
                          {data.preclinical_evidence.human_genetics.monogenic_mutations.map((item, i) => (
                            <tr key={i}>
                              <td>{item.variant}</td>
                              <td>{item.phenotype}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <div>
                      <strong>Common/Low-Frequency Variant Associations:</strong>
                      <table className="evidence-table" style={{ marginTop: '0.5rem' }}>
                        <thead>
                          <tr>
                            <th>Variant</th>
                            <th>Association</th>
                          </tr>
                        </thead>
                        <tbody>
                          {data.preclinical_evidence.human_genetics.common_variants.map((item, i) => (
                            <tr key={i}>
                              <td>{item.variant}</td>
                              <td>{item.association}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                  <div className="subsection">
                    <h4>Preclinical Animal Studies</h4>
                    <div style={{ marginBottom: '1rem' }}>
                      <strong>Loss-of-Function Models:</strong>
                      <table className="evidence-table" style={{ marginTop: '0.5rem' }}>
                        <thead>
                          <tr>
                            <th>Model</th>
                            <th>Outcome</th>
                          </tr>
                        </thead>
                        <tbody>
                          {data.preclinical_evidence.animal_models.loss_of_function.map((item, i) => (
                            <tr key={i}>
                              <td>{item.model}</td>
                              <td>{item.outcome}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <div>
                      <strong>Gain-of-Function Models:</strong>
                      <table className="evidence-table" style={{ marginTop: '0.5rem' }}>
                        <thead>
                          <tr>
                            <th>Model</th>
                            <th>Outcome</th>
                          </tr>
                        </thead>
                        <tbody>
                          {data.preclinical_evidence.animal_models.gain_of_function.map((item, i) => (
                            <tr key={i}>
                              <td>{item.model}</td>
                              <td>{item.outcome}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}

              {/* Drug/Trial Landscape */}
              {renderSection(
                '4. Drug/Trial Landscape',
                <div className="landscape-section">
                  <div className="subsection">
                    <h4>Market Summary</h4>
                    <p>{data.drug_trial_landscape.summary}</p>
                  </div>
                  <div className="subsection">
                    <h4>Key Competitive Assets</h4>
                    <table className="competitors-table">
                      <thead>
                        <tr>
                          <th>Company</th>
                          <th>Molecule</th>
                          <th>Phase</th>
                          <th>Mechanism</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.drug_trial_landscape.competitors.map((comp, i) => (
                          <tr key={i}>
                            <td>{comp.company}</td>
                            <td>{comp.molecule_name}</td>
                            <td>
                              <span className={`phase-badge phase-${comp.phase.toLowerCase().replace(/\s/g, '-')}`}>
                                {comp.phase}
                              </span>
                            </td>
                            <td>{comp.mechanism}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div className="phase-distribution">
                    <h4>Pipeline Distribution</h4>
                    <div className="phase-bars">
                      {Object.entries(data.drug_trial_landscape.phase_count).map(([phase, count]) => (
                        <div key={phase} className="phase-bar-item">
                          <span className="phase-label">{phase.replace(/([A-Z])/g, ' $1').trim()}:</span>
                          <div className="phase-bar">
                            <div className="phase-fill" style={{ width: `${Math.min(count * 10, 100)}%` }}>
                              {count}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Patent & IP */}
              {renderSection(
                '5. Patent & IP Landscape',
                <div className="ip-section">
                  <div className="subsection">
                    <h4>Recent Filings</h4>
                    <table className="patent-table">
                      <thead>
                        <tr>
                          <th>Assignee</th>
                          <th>Year</th>
                          <th>Focus</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.patent_ip.recent_filings.map((filing, i) => (
                          <tr key={i}>
                            <td>{filing.assignee}</td>
                            <td>{filing.year}</td>
                            <td>{filing.focus}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div className="subsection">
                    <h4>IP Strategy</h4>
                    <div className="strategy-box">
                      {data.patent_ip.strategy}
                    </div>
                  </div>
                </div>
              )}

              {/* Indication Potential */}
              {renderSection(
                '6. Indication Potential',
                <div className="potential-section">
                  <div className="score-display">
                    <div className="score-circle">
                      <span className="score-number">{data.indication_potential.score}</span>
                      <span className="score-max">/10</span>
                    </div>
                    <div className="score-reasoning">
                      <h4>Scoring Rationale</h4>
                      <p>{data.indication_potential.reasoning}</p>
                    </div>
                  </div>
                  <div className="analysis-text">
                    <h4>Current Therapeutic Landscape</h4>
                    <div style={{ marginBottom: '1rem' }}>
                      <strong>Major Drug Classes:</strong>
                      <ul style={{ marginTop: '0.5rem', paddingLeft: '1.5rem' }}>
                        {data.indication_specific_analysis.therapeutic_classes.map((tc, i) => (
                          <li key={i} style={{ marginBottom: '0.25rem' }}>
                            <strong>{tc.class_name}:</strong> {tc.examples}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <strong>Treatment Guidelines:</strong>
                      <p style={{ marginTop: '0.5rem' }}>{data.indication_specific_analysis.treatment_guidelines}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Differentiation */}
              {renderSection(
                '7. Key Differentiation',
                <div className="diff-section">
                  <p className="diff-analysis">{data.differentiation.analysis}</p>
                  <div className="diff-grid">
                    <div className="diff-box advantages">
                      <h4>✓ Advantages</h4>
                      <ul>
                        {data.differentiation.advantages.map((adv, i) => (
                          <li key={i}>{adv}</li>
                        ))}
                      </ul>
                    </div>
                    <div className="diff-box disadvantages">
                      <h4>✗ Challenges</h4>
                      <ul>
                        {data.differentiation.disadvantages.map((dis, i) => (
                          <li key={i}>{dis}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              )}

              {/* Unmet Needs */}
              {renderSection(
                '8. Unmet Medical Needs',
                <div className="unmet-grid" style={{ gridTemplateColumns: 'repeat(2, 1fr)' }}>
                  <div className="unmet-box">
                    <h4>📊 Incomplete Response</h4>
                    <p>{data.unmet_needs.response_rates}</p>
                  </div>
                  <div className="unmet-box">
                    <h4>⚠️ Treatment Resistance</h4>
                    <p>{data.unmet_needs.resistance}</p>
                  </div>
                  <div className="unmet-box">
                    <h4>🛡️ Safety Limitations</h4>
                    <p>{data.unmet_needs.safety_limitations}</p>
                  </div>
                  <div className="unmet-box">
                    <h4>💊 Adherence Challenges</h4>
                    <p>{data.unmet_needs.adherence_challenges}</p>
                  </div>
                </div>
              )}

              {/* Risk Assessment */}
              {renderSection(
                '9. Risk Assessment',
                <div className="risk-section">
                  <div className="risk-analysis">
                    <h4>Assessment Summary</h4>
                    <p>{data.risks.risk_analysis}</p>
                  </div>
                  <div className="risk-scores">
                    <div className="risk-score-item">
                      <span className="risk-label">Clinical Risk</span>
                      <div className="risk-bar">
                        <div
                          className={`risk-fill ${data.risks.clinical > 50 ? 'high' : 'low'}`}
                          style={{ width: `${data.risks.clinical}%` }}
                        >
                          {data.risks.clinical}
                        </div>
                      </div>
                    </div>
                    <div className="risk-score-item">
                      <span className="risk-label">Safety Risk</span>
                      <div className="risk-bar">
                        <div
                          className={`risk-fill ${data.risks.safety > 50 ? 'high' : 'low'}`}
                          style={{ width: `${data.risks.safety}%` }}
                        >
                          {data.risks.safety}
                        </div>
                      </div>
                    </div>
                    <div className="risk-score-item">
                      <span className="risk-label">Competitive Risk</span>
                      <div className="risk-bar">
                        <div
                          className={`risk-fill ${data.risks.competitive > 50 ? 'high' : 'low'}`}
                          style={{ width: `${data.risks.competitive}%` }}
                        >
                          {data.risks.competitive}
                        </div>
                      </div>
                    </div>
                    <div className="risk-score-item">
                      <span className="risk-label">Technical Risk</span>
                      <div className="risk-bar">
                        <div
                          className={`risk-fill ${data.risks.technical > 50 ? 'high' : 'low'}`}
                          style={{ width: `${data.risks.technical}%` }}
                        >
                          {data.risks.technical}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Biomarker Strategy */}
              {renderSection(
                '10. Biomarker Strategy',
                <div className="biomarker-section">
                  <div style={{ marginBottom: '1rem' }}>
                    <h4 style={{ fontSize: '0.9375rem', marginBottom: '0.5rem', color: '#0f172a' }}>Stratification Biomarkers:</h4>
                    <ul style={{ paddingLeft: '1.5rem', listStyleType: 'disc' }}>
                      {data.biomarker_strategy.stratification_biomarkers.map((biomarker, i) => (
                        <li key={i} style={{ marginBottom: '0.375rem', fontSize: '0.8125rem' }}>{biomarker}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <h4 style={{ fontSize: '0.9375rem', marginBottom: '0.5rem', color: '#0f172a' }}>Adaptive Design Considerations:</h4>
                    <p style={{ fontSize: '0.8125rem', lineHeight: '1.5' }}>{data.biomarker_strategy.adaptive_design}</p>
                  </div>
                </div>
              )}

              {/* Business Development */}
              {renderSection(
                '11. Business Development & Investment',
                <div className="bd-section">
                  <div className="subsection">
                    <h4>Recent Activities</h4>
                    <div className="bd-activities">
                      {data.bd_potentials.activities.map((act, i) => (
                        <div key={i} className="bd-activity-item">
                          <div className="activity-icon">
                            {act.company.substring(0, 2).toUpperCase()}
                          </div>
                          <div className="activity-content">
                            <h5>{act.company}</h5>
                            <p>{act.description}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="subsection">
                    <h4>Interested Parties</h4>
                    <div className="interested-parties">
                      {data.bd_potentials.interested_parties.map((party, i) => (
                        <span key={i} className="party-tag">{party}</span>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        ) : null}
      </main>
    </div>
  );
}

export default TargetAnalyzer;
