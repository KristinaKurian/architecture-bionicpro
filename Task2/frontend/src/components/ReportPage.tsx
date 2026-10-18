import React, { useEffect, useState } from 'react';

const API = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const yesterdayUtc = () => {
  const now = new Date();
  now.setUTCDate(now.getUTCDate() - 1);
  return now.toISOString().slice(0, 10);
};

const ReportPage: React.FC = () => {
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);
  const [csrf, setCsrf] = useState('');
  const [start, setStart] = useState(yesterdayUtc);
  const [end, setEnd] = useState(yesterdayUtc);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetch(`${API}/auth/me`, { credentials: 'include' })
      .then(async r => {
        if (!r.ok) return setAuthenticated(false);
        const result = await r.json();
        setCsrf(result.csrf);
        setAuthenticated(true);
      })
      .catch(() => { setError('Нет связи с API'); setAuthenticated(false); });
  }, []);

  const download = async () => {
    setLoading(true);
    setError('');
    try {
      const params = new URLSearchParams({ from_date: start, to_date: end });
      const response = await fetch(`${API}/reports?${params}`, { credentials: 'include' });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        const messages: Record<number, string> = {
          401: 'Войдите в систему.',
          403: 'Нет прав на запрошенные данные.',
          409: 'Этот период ещё не обработан Airflow. Выберите готовые даты.'
        };
        throw new Error(messages[response.status] || body.detail || `HTTP ${response.status}`);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `bionicpro-report-${start}-${end}.csv`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : 'Ошибка скачивания');
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    try {
      const response = await fetch(`${API}/auth/logout`, {
        method: 'POST', credentials: 'include', headers: { 'X-CSRF-Token': csrf }
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      setAuthenticated(false);
    } catch { setError('Не удалось выйти из системы'); }
  };

  return (
    <div style={{ maxWidth: 550, margin: '64px auto', fontFamily: 'Arial' }}>
      <h1>Отчёт о работе протеза</h1>
      {authenticated === null ? <p>Проверяем авторизацию…</p> :
        !authenticated ? <a href={`${API}/auth/login`}>Войти</a> : (
          <>
            <p>Вы можете получить отчёт только о собственных протезах.</p>
            <label>С: <input type="date" value={start} onChange={e => setStart(e.target.value)} /></label>{' '}
            <label>По: <input type="date" value={end} onChange={e => setEnd(e.target.value)} /></label>
            <div style={{ marginTop: 24 }}>
              <button onClick={download} disabled={loading || !start || !end}>
                {loading ? 'Готовим файл…' : 'Скачать CSV-отчёт'}
              </button>{' '}
              <button onClick={logout}>Выйти</button>
            </div>
          </>
        )}
      {error && <p role="alert" style={{ color: 'darkred' }}>{error}</p>}
    </div>
  );
};

export default ReportPage;
