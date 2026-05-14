import { render, screen, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from './AuthContext';
import { authAPI } from '../services/api';

jest.mock('../services/api', () => ({
  authAPI: {
    getMe: jest.fn(),
    claimHistory: jest.fn(),
  },
  getGuestId: jest.fn(() => 'guest-id'),
}));

function AuthProbe() {
  const { user, loading } = useAuth();
  if (loading) return <span>加载中</span>;
  return <span>{user?.email || '未登录'}</span>;
}

test('stores OAuth token from URL fragment and loads the Google user', async () => {
  window.localStorage.clear();
  window.history.replaceState({}, '', '/#auth_token=jwt-token');
  authAPI.getMe.mockResolvedValueOnce({ id: 1, email: 'google@example.com' });

  render(
    <AuthProvider>
      <AuthProbe />
    </AuthProvider>
  );

  await waitFor(() => {
    expect(screen.getByText('google@example.com')).toBeInTheDocument();
  });
  expect(window.localStorage.getItem('access_token')).toBe('jwt-token');
  expect(window.location.hash).toBe('');
});
