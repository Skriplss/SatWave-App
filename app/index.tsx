import { Redirect } from 'expo-router';
import React from 'react';
import { useAuth } from '@/contexts/auth-context';

export default function Index() {
  const { session, loading } = useAuth();
  if (loading) return null;
  return <Redirect href={session ? '/forum' : '/(auth)/sign-in'} />;
}
