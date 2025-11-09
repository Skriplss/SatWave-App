import createContextHook from '@nkzw/create-context-hook';
import { useEffect, useMemo, useState, useCallback } from 'react';
import { supabase } from '@/lib/supabase';
import { router } from 'expo-router';

export type AuthSession = {
  userId: string;
  email?: string | null;
};

type AuthContextValue = {
  session: AuthSession | null;
  loading: boolean;
  signOut: () => Promise<void>;
};

export const [AuthProvider, useAuth] = createContextHook<AuthContextValue>(() => {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    // Initialize from current session
    supabase.auth.getSession().then(({ data }) => {
      if (!mounted) return;
      const s = data.session;
      setSession(s ? { userId: s.user.id, email: s.user.email } : null);
      setLoading(false);
    });
    // Subscribe to changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, s) => {
      setSession(s ? { userId: s.user.id, email: s.user.email } : null);
    });
    return () => {
      mounted = false;
      subscription?.unsubscribe();
    };
  }, []);

  const signOut = useCallback(async () => {
    const { error } = await supabase.auth.signOut();
    if (error) throw error;
    // Force local state + navigation
    setSession(null);
    router.replace('/forum');
  }, []);

  return useMemo(
    () => ({ session, loading, signOut }),
    [session, loading, signOut]
  );
});
