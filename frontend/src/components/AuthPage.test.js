import { render, screen } from '@testing-library/react';
import AuthPage from './AuthPage';
import { AuthProvider } from '../contexts/AuthContext';

test('offers Google login through the backend OAuth endpoint', () => {
  render(
    <AuthProvider>
      <AuthPage />
    </AuthProvider>
  );

  const googleLogin = screen.getByRole('link', { name: /使用 Google 登录/ });

  expect(googleLogin).toHaveAttribute(
    'href',
    'http://localhost:8003/api/auth/google/login'
  );
});
