import { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, ActivityIndicator } from 'react-native';
import { router, Link } from 'expo-router';
import { supabase } from '@/lib/supabase';
import Colors from '@/constants/colors';

export default function SignUpScreen() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const onSignUp = async () => {
    setError(null);
    setInfo(null);
    if (!email || !password) {
      setError('Enter email and password');
      return;
    }
    setLoading(true);
    try {
      const { data, error: err } = await supabase.auth.signUp({
        email,
        password,
      });
      if (err) {
        setError(err.message);
        return;
      }
      if (data.session) {
        router.replace('/forum');
      } else {
        setInfo('Check your email to confirm registration.');
      }
    } catch (e: any) {
      setError(e?.message || 'Sign-up error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.card}>
        <Text style={styles.title}>Sign Up</Text>
        <TextInput
          placeholder="Email"
          placeholderTextColor={Colors.textLight}
          keyboardType="email-address"
          autoCapitalize="none"
          value={email}
          onChangeText={setEmail}
          style={styles.input}
        />
        <TextInput
          placeholder="Password"
          placeholderTextColor={Colors.textLight}
          secureTextEntry
          value={password}
          onChangeText={setPassword}
          style={styles.input}
        />
        {!!error && <Text style={styles.error}>{error}</Text>}
        {!!info && <Text style={styles.info}>{info}</Text>}
        <TouchableOpacity style={styles.button} onPress={onSignUp} disabled={loading}>
          {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.buttonText}>Create Account</Text>}
        </TouchableOpacity>
        <Text style={styles.linkText}>
          Already have an account?{' '}
          <Link href="/(auth)/sign-in" style={styles.link}>
            Sign In
          </Link>
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: Colors.background, padding: 16 },
  card: { width: '100%', maxWidth: 420, backgroundColor: Colors.surface, borderRadius: 16, padding: 20, gap: 12, borderWidth: 1, borderColor: Colors.border },
  title: { fontSize: 24, fontWeight: '700', color: Colors.text, textAlign: 'center', marginBottom: 8 },
  input: { backgroundColor: Colors.background, borderWidth: 1, borderColor: Colors.border, borderRadius: 10, padding: 14, color: Colors.text, fontSize: 16 },
  button: { backgroundColor: Colors.primary, paddingVertical: 14, borderRadius: 10, alignItems: 'center', marginTop: 4 },
  buttonText: { color: '#fff', fontSize: 16, fontWeight: '700' },
  linkText: { color: Colors.textSecondary, textAlign: 'center', marginTop: 4 },
  link: { color: Colors.accent, fontWeight: '700' },
  error: { color: Colors.error, fontSize: 14 },
  info: { color: Colors.textSecondary, fontSize: 14 },
});

