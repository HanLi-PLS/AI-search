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
      const requestBody = {
        target: target.trim(),
        indication: indication.trim()
      };
      const config = {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      };

      // Call all 3 parallel endpoints simultaneously for higher quality output
      console.log('Starting parallel analysis calls...');
      const [coreBioResponse, marketCompResponse, strategyRiskResponse] = await Promise.all([
        axios.post('/api/target-analyzer/analyze-core-biology', requestBody, config),
        axios.post('/api/target-analyzer/analyze-market-competition', requestBody, config),
        axios.post('/api/target-analyzer/analyze-strategy-risk', requestBody, config)
      ]);
      console.log('All parallel calls completed!');

      // Merge results from all 3 endpoints
      const mergedData = {
        target: coreBioResponse.data.target,
        indication: coreBioResponse.data.indication,
        biological_overview: coreBioResponse.data.biological_overview,
        therapeutic_rationale: coreBioResponse.data.therapeutic_rationale,
        preclinical_evidence: coreBioResponse.data.preclinical_evidence,
        drug_trial_landscape: marketCompResponse.data.drug_trial_landscape,
        patent_ip: marketCompResponse.data.patent_ip,
        indication_potential: marketCompResponse.data.indication_potential,
        differentiation: marketCompResponse.data.differentiation,
        unmet_needs: strategyRiskResponse.data.unmet_needs,
        indication_specific_analysis: strategyRiskResponse.data.indication_specific_analysis,
        risks: strategyRiskResponse.data.risks,
        biomarker_strategy: strategyRiskResponse.data.biomarker_strategy,
        bd_potentials: strategyRiskResponse.data.bd_potentials,
      };

      setData(mergedData);
    } catch (err) {
      console.error('Analysis error:', err);
      setError(err.response?.data?.detail || 'Failed to generate analysis. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleExportHTML = () => {
    const content = document.getElementById('exportable-content');
    if (!content) return;

    const htmlContent = `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${data.target} for ${data.indication} - Target Analysis</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 1200px; margin: 0 auto; padding: 2rem; background: #f8fafc; }
    h1 { color: #0f172a; border-bottom: 3px solid #2563eb; padding-bottom: 1rem; }
    .section-card { background: white; border-radius: 10px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    h3 { color: #0f172a; font-size: 1.25rem; border-bottom: 2px solid #e2e8f0; padding-bottom: 0.5rem; }
    table { width: 100%; border-collapse: collapse; margin: 1rem 0; }
    th, td { padding: 0.75rem; text-align: left; border-bottom: 1px solid #e2e8f0; }
    th { background: #f8fafc; font-weight: 600; }
    img { max-width: 100%; height: auto; }
  </style>
</head>
<body>
  <h1>${data.target} for ${data.indication}</h1>
  ${content.innerHTML}
</body>
</html>`;

    const blob = new Blob([htmlContent], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${data.target}_${data.indication}_Analysis.html`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleExportPDF = async () => {
    // Dynamically import html2pdf
    const html2pdf = (await import('html2pdf.js')).default;

    const content = document.getElementById('exportable-content');
    if (!content) return;

    const opt = {
      margin: 0.5,
      filename: `${data.target}_${data.indication}_Analysis.pdf`,
      image: { type: 'jpeg', quality: 0.98 },
      html2canvas: { scale: 2, useCORS: true },
      jsPDF: { unit: 'in', format: 'letter', orientation: 'portrait' }
    };

    // Clone content and add title
    const wrapper = document.createElement('div');
    const title = document.createElement('h1');
    title.textContent = `${data.target} for ${data.indication}`;
    title.style.cssText = 'color: #0f172a; border-bottom: 3px solid #2563eb; padding-bottom: 1rem; margin-bottom: 1.5rem;';
    wrapper.appendChild(title);
    wrapper.appendChild(content.cloneNode(true));

    html2pdf().set(opt).from(wrapper).save();
  };

  const renderPubMedLink = (pmid) => {
    if (!pmid) return null;
    return (
      <a
        href={`https://pubmed.ncbi.nlm.nih.gov/${pmid}/`}
        target="_blank"
        rel="noopener noreferrer"
        className="pubmed-link"
        title="View on PubMed"
      >
        📚 PMID: {pmid}
      </a>
    );
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
              <div className="header-actions">
                <button className="export-btn" onClick={handleExportHTML} title="Export as HTML">
                  📄 HTML
                </button>
                <button className="export-btn" onClick={handleExportPDF} title="Export as PDF">
                  📑 PDF
                </button>
                <button className="new-analysis-btn" onClick={() => setData(null)}>
                  New Analysis
                </button>
              </div>
            </div>

            <div className="results-layout">
              {/* Side Navigation Bar */}
              <aside className="side-nav-bar">
                <div className="side-nav-header">Sections</div>
                <nav className="side-nav-items">
                  <a href="#section-1" className="nav-item">
                    <span className="nav-number">1</span>
                    <span className="nav-text">Biological Overview</span>
                  </a>
                  <a href="#section-2" className="nav-item">
                    <span className="nav-number">2</span>
                    <span className="nav-text">Therapeutic Rationale</span>
                  </a>
                  <a href="#section-3" className="nav-item">
                    <span className="nav-number">3</span>
                    <span className="nav-text">Pre-clinical Evidence</span>
                  </a>
                  <a href="#section-4" className="nav-item">
                    <span className="nav-number">4</span>
                    <span className="nav-text">Drug/Trial Landscape</span>
                  </a>
                  <a href="#section-5" className="nav-item">
                    <span className="nav-number">5</span>
                    <span className="nav-text">Patent & IP</span>
                  </a>
                  <a href="#section-6" className="nav-item">
                    <span className="nav-number">6</span>
                    <span className="nav-text">Indication Potential</span>
                  </a>
                  <a href="#section-7" className="nav-item">
                    <span className="nav-number">7</span>
                    <span className="nav-text">Differentiation</span>
                  </a>
                  <a href="#section-8" className="nav-item">
                    <span className="nav-number">8</span>
                    <span className="nav-text">Unmet Needs</span>
                  </a>
                  <a href="#section-9" className="nav-item">
                    <span className="nav-number">9</span>
                    <span className="nav-text">Risks</span>
                  </a>
                  <a href="#section-10" className="nav-item">
                    <span className="nav-number">10</span>
                    <span className="nav-text">Biomarker Strategy</span>
                  </a>
                  <a href="#section-11" className="nav-item">
                    <span className="nav-number">11</span>
                    <span className="nav-text">BD Potential</span>
                  </a>
                </nav>
              </aside>

              <div className="results-content" id="exportable-content">

              {/* Biological Overview */}
              <div id="section-1">
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
                      {data.biological_overview.human_validation_pmid && (
                        <div style={{ marginTop: '0.5rem' }}>
                          {renderPubMedLink(data.biological_overview.human_validation_pmid)}
                        </div>
                      )}
                    </div>
                    <div>
                      <h4>Species Conservation</h4>
                      <p>{data.biological_overview.species_conservation}</p>
                      {data.biological_overview.species_conservation_pmid && (
                        <div style={{ marginTop: '0.5rem' }}>
                          {renderPubMedLink(data.biological_overview.species_conservation_pmid)}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
              </div>

              {/* Therapeutic Rationale */}
              <div id="section-2">
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
              </div>

              {/* Pre-clinical Evidence */}
              <div id="section-3">
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
                            <th>Effect Size</th>
                            <th>Quality</th>
                            <th>Benchmark</th>
                            <th>Citation</th>
                          </tr>
                        </thead>
                        <tbody>
                          {data.preclinical_evidence.human_genetics.monogenic_mutations.map((item, i) => (
                            <tr key={i}>
                              <td>{item.variant}</td>
                              <td>{item.phenotype}</td>
                              <td>{item.effect_size || '—'}</td>
                              <td>
                                {item.evidence_quality && (
                                  <span className={`quality-badge quality-${item.evidence_quality.toLowerCase()}`}>
                                    {item.evidence_quality}
                                  </span>
                                )}
                              </td>
                              <td style={{ fontSize: '0.8125rem', color: '#475569' }}>{item.benchmark_comparison || '—'}</td>
                              <td>{item.pmid ? renderPubMedLink(item.pmid) : '—'}</td>
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
                            <th>Significance</th>
                            <th>Quality</th>
                            <th>Benchmark</th>
                            <th>Citation</th>
                          </tr>
                        </thead>
                        <tbody>
                          {data.preclinical_evidence.human_genetics.common_variants.map((item, i) => (
                            <tr key={i}>
                              <td>{item.variant}</td>
                              <td>{item.association}</td>
                              <td>{item.statistical_significance || '—'}</td>
                              <td>
                                {item.evidence_quality && (
                                  <span className={`quality-badge quality-${item.evidence_quality.toLowerCase()}`}>
                                    {item.evidence_quality}
                                  </span>
                                )}
                              </td>
                              <td style={{ fontSize: '0.8125rem', color: '#475569' }}>{item.benchmark_comparison || '—'}</td>
                              <td>{item.pmid ? renderPubMedLink(item.pmid) : '—'}</td>
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
                            <th>Magnitude</th>
                            <th>Quality</th>
                            <th>Benchmark</th>
                            <th>Citation</th>
                          </tr>
                        </thead>
                        <tbody>
                          {data.preclinical_evidence.animal_models.loss_of_function.map((item, i) => (
                            <tr key={i}>
                              <td>{item.model}</td>
                              <td>{item.outcome}</td>
                              <td>{item.phenotype_magnitude || '—'}</td>
                              <td>
                                {item.evidence_quality && (
                                  <span className={`quality-badge quality-${item.evidence_quality.toLowerCase()}`}>
                                    {item.evidence_quality}
                                  </span>
                                )}
                              </td>
                              <td style={{ fontSize: '0.8125rem', color: '#475569' }}>{item.benchmark_comparison || '—'}</td>
                              <td>{item.pmid ? renderPubMedLink(item.pmid) : '—'}</td>
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
                            <th>Quality</th>
                            <th>Benchmark</th>
                            <th>Citation</th>
                          </tr>
                        </thead>
                        <tbody>
                          {data.preclinical_evidence.animal_models.gain_of_function.map((item, i) => (
                            <tr key={i}>
                              <td>{item.model}</td>
                              <td>{item.outcome}</td>
                              <td>
                                {item.evidence_quality && (
                                  <span className={`quality-badge quality-${item.evidence_quality.toLowerCase()}`}>
                                    {item.evidence_quality}
                                  </span>
                                )}
                              </td>
                              <td style={{ fontSize: '0.8125rem', color: '#475569' }}>{item.benchmark_comparison || '—'}</td>
                              <td>{item.pmid ? renderPubMedLink(item.pmid) : '—'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}
              </div>

              {/* Drug/Trial Landscape */}
              <div id="section-4">
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
              </div>

              {/* Patent & IP */}
              <div id="section-5">
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
              </div>

              {/* Indication Potential */}
              <div id="section-6">
              {renderSection(
                '6. Indication Potential',
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                  {/* Score and Rationale - Compact Row */}
                  <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'flex-start' }}>
                    <div className="score-circle">
                      <span className="score-number">{data.indication_potential.score}</span>
                      <span className="score-max">/10</span>
                    </div>
                    <div style={{ flex: 1 }}>
                      <h4 style={{ fontSize: '0.9375rem', marginBottom: '0.5rem', color: '#0f172a' }}>Scoring Rationale</h4>
                      <p style={{ fontSize: '0.8125rem', lineHeight: '1.5', color: '#475569' }}>{data.indication_potential.reasoning}</p>
                    </div>
                  </div>

                  {/* Therapeutic Landscape - Full Width */}
                  <div style={{
                    background: '#f8fafc',
                    padding: '1rem',
                    borderRadius: '8px',
                    border: '1px solid #e2e8f0'
                  }}>
                    <h4 style={{ fontSize: '0.9375rem', marginBottom: '0.75rem', color: '#0f172a' }}>Current Therapeutic Landscape</h4>
                    <div style={{ marginBottom: '1rem' }}>
                      <strong style={{ fontSize: '0.875rem', color: '#334155' }}>Major Drug Classes:</strong>
                      <ul style={{ marginTop: '0.5rem', paddingLeft: '1.5rem' }}>
                        {data.indication_specific_analysis.therapeutic_classes.map((tc, i) => (
                          <li key={i} style={{ marginBottom: '0.25rem', fontSize: '0.8125rem', lineHeight: '1.5' }}>
                            <strong>{tc.class_name}:</strong> {tc.examples}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <strong style={{ fontSize: '0.875rem', color: '#334155' }}>Treatment Guidelines:</strong>
                      <p style={{ marginTop: '0.5rem', fontSize: '0.8125rem', lineHeight: '1.5', color: '#475569' }}>
                        {data.indication_specific_analysis.treatment_guidelines}
                      </p>
                    </div>
                  </div>
                </div>
              )}
              </div>

              {/* Differentiation */}
              <div id="section-7">
              {renderSection(
                '7. Key Differentiation',
                <div className="diff-section">
                  <p className="diff-analysis">{data.differentiation.analysis}</p>

                  {/* Efficacy/Safety Position */}
                  {data.differentiation.efficacy_safety_position && (
                    <div style={{ marginTop: '1rem', marginBottom: '1rem' }}>
                      <strong style={{ fontSize: '0.875rem', color: '#334155' }}>Efficacy/Safety Frontier Position: </strong>
                      <span className={`position-badge position-${data.differentiation.efficacy_safety_position.toLowerCase()}`}>
                        {data.differentiation.efficacy_safety_position}
                      </span>
                    </div>
                  )}

                  {/* Quantified Gaps */}
                  {data.differentiation.quantified_gaps && data.differentiation.quantified_gaps.length > 0 && (
                    <div style={{ marginTop: '1rem', marginBottom: '1rem' }}>
                      <h4 style={{ fontSize: '0.9375rem', marginBottom: '0.5rem', color: '#0f172a' }}>Quantified Competitive Advantages:</h4>
                      <ul style={{ paddingLeft: '1.5rem', listStyleType: 'disc' }}>
                        {data.differentiation.quantified_gaps.map((gap, i) => (
                          <li key={i} style={{ marginBottom: '0.375rem', fontSize: '0.8125rem', fontWeight: '600', color: '#059669' }}>{gap}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Competitive Scenarios */}
                  {data.differentiation.competitive_scenarios && data.differentiation.competitive_scenarios.length > 0 && (
                    <div style={{ marginTop: '1rem', marginBottom: '1rem' }}>
                      <h4 style={{ fontSize: '0.9375rem', marginBottom: '0.5rem', color: '#0f172a' }}>Competitive Scenarios:</h4>
                      <table className="evidence-table" style={{ marginTop: '0.5rem' }}>
                        <thead>
                          <tr>
                            <th>Scenario</th>
                            <th>Probability</th>
                            <th>Impact</th>
                            <th>Strategic Response</th>
                          </tr>
                        </thead>
                        <tbody>
                          {data.differentiation.competitive_scenarios.map((scenario, i) => (
                            <tr key={i}>
                              <td>{scenario.scenario}</td>
                              <td><span className="probability-badge">{scenario.probability}</span></td>
                              <td style={{ fontSize: '0.8125rem', color: '#475569' }}>{scenario.impact}</td>
                              <td style={{ fontSize: '0.8125rem', color: '#475569' }}>{scenario.strategic_response}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

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
              </div>

              {/* Unmet Needs */}
              <div id="section-8">
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
              </div>

              {/* Risk Assessment */}
              <div id="section-9">
              {renderSection(
                '9. Risk Assessment',
                <div className="risk-section">
                  <div className="risk-analysis">
                    <h4>Executive Summary</h4>
                    <p>{data.risks.summary}</p>
                  </div>

                  {data.risks.risk_items && data.risks.risk_items.length > 0 && (
                    <div style={{ marginTop: '1.5rem' }}>
                      <h4 style={{ fontSize: '0.9375rem', marginBottom: '1rem', color: '#0f172a' }}>Detailed Risk Analysis:</h4>
                      <div className="risk-items-container">
                        {data.risks.risk_items.map((risk, i) => (
                          <div key={i} className="risk-item-card">
                            <div className="risk-item-header">
                              <span className={`risk-category-badge category-${risk.category.toLowerCase()}`}>
                                {risk.category}
                              </span>
                              <div className="risk-scores-inline">
                                <div className="risk-score-mini">
                                  <span className="score-label">Probability:</span>
                                  <div className="score-bar-mini">
                                    <div
                                      className={`score-fill-mini ${risk.probability > 50 ? 'high' : 'medium'}`}
                                      style={{ width: `${risk.probability}%` }}
                                    >
                                      {risk.probability}%
                                    </div>
                                  </div>
                                </div>
                                <div className="risk-score-mini">
                                  <span className="score-label">Impact:</span>
                                  <div className="score-bar-mini">
                                    <div
                                      className={`score-fill-mini ${risk.impact > 50 ? 'high' : 'medium'}`}
                                      style={{ width: `${risk.impact}%` }}
                                    >
                                      {risk.impact}%
                                    </div>
                                  </div>
                                </div>
                              </div>
                            </div>
                            <div className="risk-item-content">
                              <div className="risk-field">
                                <strong>Description:</strong>
                                <p>{risk.description}</p>
                              </div>
                              <div className="risk-field">
                                <strong>Timeline:</strong>
                                <p>{risk.timeline}</p>
                              </div>
                              <div className="risk-field">
                                <strong>Early Warning Signals:</strong>
                                <p>{risk.early_warning_signals}</p>
                              </div>
                              <div className="risk-field">
                                <strong>Mitigation Strategies:</strong>
                                <p>{risk.mitigation_strategies}</p>
                              </div>
                              <div className="risk-field">
                                <strong>Evidence Quality:</strong>
                                <span className={`quality-badge quality-${risk.evidence_quality.toLowerCase()}`}>
                                  {risk.evidence_quality}
                                </span>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
              </div>

              {/* Biomarker Strategy */}
              <div id="section-10">
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
              </div>

              {/* Business Development */}
              <div id="section-11">
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
            </div>
          </div>
        ) : null}
      </main>
    </div>
  );
}

export default TargetAnalyzer;
