import { useEffect, useState } from 'react';
import './App.css';
import LandingPage from './pages/LandingPage';
import MockExamPage from './pages/MockExamPage';
import {
  getBundleFromProcessResponse,
  isValidExamBundle,
  loadStoredExamBundle,
  loadStoredExamId,
  setMockExamLocation,
  storeExamBundle,
  withExamAssetUrls,
} from './lib/examStorage';

function App() {
  const [activeExamBundle, setActiveExamBundle] = useState(() => loadStoredExamBundle());
  const [activeExamId, setActiveExamId] = useState(() => loadStoredExamId());
  const [view, setView] = useState(() => getInitialView(activeExamBundle));

  useEffect(() => {
    function handleLocationChange() {
      setView(getInitialView(loadStoredExamBundle()));
    }

    window.addEventListener('popstate', handleLocationChange);
    return () => window.removeEventListener('popstate', handleLocationChange);
  }, []);

  if (view === 'mock-exam') {
    return (
      <MockExamPage
        initialBundle={activeExamBundle || loadStoredExamBundle()}
        examId={activeExamId}
        loadLabel={activeExamId ? `Generated exam ${activeExamId}` : 'Generated exam'}
      />
    );
  }

  return (
    <LandingPage
      onExamReady={(response) => {
        const examId = response.exam_id || response.examId || null;
        const bundle = withExamAssetUrls(getBundleFromProcessResponse(response), examId);
        setActiveExamId(examId);
        setActiveExamBundle(bundle);
        storeExamBundle(bundle, examId);
        setMockExamLocation();
        setView('mock-exam');
      }}
    />
  );
}

function getInitialView(storedBundle) {
  return window.location.hash === '#mock-exam' && isValidExamBundle(storedBundle)
    ? 'mock-exam'
    : 'landing';
}

export default App;

