import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity, ActivityIndicator, Image, RefreshControl, Alert } from 'react-native';
import * as Linking from 'expo-linking';
import Colors from '@/constants/colors';
import { useAuth } from '@/contexts/auth-context';
import type { Coupon } from '@/types/coupon';
import { fetchCoupons, loadRedeemed, markRedeemed, isExpired, fetchUserRedemptions, upsertRedemption } from '@/lib/coupons';
import { apiAuthPost } from '@/lib/api';

export default function CouponsScreen() {
  const { session } = useAuth();
  const [data, setData] = useState<Coupon[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [redeemed, setRedeemed] = useState<Record<string, number>>({});
  const [confirmVisible, setConfirmVisible] = useState(false);
  const [successVisible, setSuccessVisible] = useState(false);
  const [sending, setSending] = useState(false);
  const [lastSentCode, setLastSentCode] = useState<string | null>(null);
  const [lastEmailSent, setLastEmailSent] = useState<string | null>(null);
  const [pending, setPending] = useState<{
    id: string;
    code?: string | null;
    title?: string | null;
    expires_at?: string | null;
  } | null>(null);

  useEffect(() => {
    let active = true;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const [coupons, localMap, remoteMap] = await Promise.all([
          fetchCoupons().catch(() => []),
          loadRedeemed(session?.userId).catch(() => ({})),
          session?.userId ? fetchUserRedemptions(session.userId).catch(() => ({})) : Promise.resolve({}),
        ]);
        if (!active) return;
        const merged: Record<string, number> = { ...localMap, ...remoteMap };
        setData(coupons);
        setRedeemed(merged);
      } catch (e: any) {
        if (!active) return;
        setError(e.message || String(e));
      } finally {
        if (active) setLoading(false);
      }
    };
    if (session) load();
    return () => {
      active = false;
    };
  }, [session]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      const userId = session?.userId;
      setData(await fetchCoupons());
      const [localMap, remoteMap] = await Promise.all([
        loadRedeemed(userId),
        userId ? fetchUserRedemptions(userId) : Promise.resolve({}),
      ]);
      setRedeemed({ ...localMap, ...remoteMap });
    } finally {
      setRefreshing(false);
    }
  }, []);

  const openInbox = (address: string) => {
    const domain = (address.split('@')[1] || '').toLowerCase();
    let url = `mailto:${address}`;
    if (domain === 'gmail.com') url = 'https://mail.google.com/mail/u/0/#inbox';
    else if (['outlook.com', 'hotmail.com', 'live.com', 'msn.com'].includes(domain)) url = 'https://outlook.live.com/mail/0/inbox';
    else if (domain === 'yahoo.com') url = 'https://mail.yahoo.com/';
    Linking.openURL(url).catch(() => {});
  };

  const generateCode = () => {
    const alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    let s = 'SALE';
    for (let i = 0; i < 6; i++) s += alphabet[Math.floor(Math.random() * alphabet.length)];
    return s;
  };

  const handleRedeem = useCallback(async (id: string, code?: string | null, _url?: string | null, title?: string | null, expires_at?: string | null) => {
    if (!session) return;
    setPending({ id, code, title, expires_at });
    setConfirmVisible(true);
  }, [session]);

  const doSend = useCallback(async () => {
    if (!session || !pending) return;
    const email = session.email;
    if (!email) {
      Alert.alert('No Email', 'Your account has no email.');
      return;
    }
    try {
      setSending(true);
      setConfirmVisible(false);
      setSuccessVisible(true);

      setRedeemed((prev) => ({ ...prev, [pending.id]: Date.now() }));

      const code = pending.code && pending.code.trim().length > 0 ? pending.code : generateCode();
      await upsertRedemption(pending.id, session.userId);
      await apiAuthPost('/coupons/send-code', { email, code, title: pending.title, expires_at: pending.expires_at });
      await markRedeemed(pending.id, session.userId);
      setRedeemed(await loadRedeemed(session.userId));
      setLastSentCode(code);
      setLastEmailSent(email);
    } catch (e: any) {
      if (pending) {
        setRedeemed((prev) => {
          const copy = { ...prev } as Record<string, number>;
          delete copy[pending.id];
          return copy;
        });
      }
      Alert.alert('Error', e?.message || String(e));
    } finally {
      setSending(false);
    }
  }, [session, pending]);

  if (!session) {
    return (
      <View style={styles.center}>
        <Text style={styles.muted}>Login to view coupons</Text>
      </View>
    );
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={Colors.primary} />
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.center}>
        <Text style={styles.error}>Failed to load coupons: {error}</Text>
      </View>
    );
  }

  const list = data && data.length > 0 ? data : [
    {
      id: 'placeholder-eco-10',
      title: 'Eco Store 10% OFF',
      description: 'Welcome coupon for new recyclers',
      discount_percent: 10,
      code: 'GREEN10',
      expires_at: new Date(Date.now() + 30*24*60*60*1000).toISOString(),
    },
  ] as Coupon[];

  return (
    <>
      <FlatList
        contentContainerStyle={styles.list}
        data={list}
        keyExtractor={(item) => item.id}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        scrollEnabled={!confirmVisible && !successVisible}
        ListHeaderComponent={() => (
          <View style={[styles.card, { borderColor: Colors.accent }]}>
            <Text style={[styles.title, { color: Colors.accent }]}>Featured Coupon</Text>
            <Text style={styles.desc}>Save more while you save the planet 🌍</Text>
          </View>
        )}
        renderItem={({ item }) => (
          <View style={[styles.card, isExpired(item.expires_at) ? styles.cardDim : null]}>
            {item.image_url ? (
              <Image source={{ uri: item.image_url }} style={styles.image} resizeMode="cover" />
            ) : null}
            <Text style={styles.title}>{item.title}</Text>
            {item.description ? <Text style={styles.desc}>{item.description}</Text> : null}
            <View style={styles.row}>
              {item.discount_percent != null ? (
                <Text style={styles.badge}>-{item.discount_percent}%</Text>
              ) : null}
              {item.code ? <Text style={styles.code}>Code: {item.code}</Text> : null}
              {item.expires_at ? (
                <Text style={styles.exp}>Expires: {new Date(item.expires_at).toLocaleDateString()}</Text>
              ) : null}
            </View>
            <View style={styles.rowActions}>
              <TouchableOpacity
                style={[
                  styles.button,
                  redeemed[item.id] ? styles.buttonDisabled : null,
                ]}
                onPress={() => {
                  if (redeemed[item.id]) return;
                  handleRedeem(item.id, item.code, item.url, item.title, item.expires_at);
                }}
                disabled={!!redeemed[item.id]}
                accessibilityState={{ disabled: !!redeemed[item.id] }}
                activeOpacity={redeemed[item.id] ? 1 : undefined}
              >
                <Text style={[styles.buttonText, redeemed[item.id] ? styles.buttonDisabledText : null]}>
                  {redeemed[item.id] ? 'Coupon has been claimed' : 'Redeem'}
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        )}
      />

      {/* Confirm overlay (web-friendly) */}
      {confirmVisible ? (
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>Send coupon code to email?</Text>
            <Text style={styles.modalText}>The code will be sent to {session?.email}.</Text>
            <View style={styles.modalRow}>
              <TouchableOpacity style={[styles.modalBtn, styles.modalCancel]} onPress={() => setConfirmVisible(false)} disabled={sending}>
                <Text style={[styles.modalBtnText, styles.modalCancelText]}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity style={[styles.modalBtn, styles.modalOk]} onPress={doSend} disabled={sending}>
                <Text style={styles.modalOkText}>{sending ? 'Sending…' : 'Send'}</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      ) : null}

      {/* Success overlay */}
      {successVisible ? (
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>Coupon code sent</Text>
            <Text style={styles.modalText}>Please check your inbox.</Text>
            <View style={styles.modalRow}>
              <TouchableOpacity style={[styles.modalBtn, styles.modalOk, { flex: 1 }]} onPress={() => setSuccessVisible(false)}>
                <Text style={styles.modalOkText}>OK</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      ) : null}
    </>
  );
}

const styles = StyleSheet.create({
  list: { padding: 16 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: Colors.background },
  muted: { color: Colors.textSecondary },
  error: { color: Colors.error },
  card: {
    backgroundColor: '#fff', borderRadius: 16, padding: 16, marginBottom: 12, borderWidth: 1, borderColor: Colors.border,
  },
  cardDim: { opacity: 0.6 },
  image: { width: '100%', height: 140, borderRadius: 12, marginBottom: 8 },
  title: { fontSize: 16, fontWeight: '700', color: Colors.text },
  desc: { marginTop: 6, color: Colors.textSecondary },
  row: { flexDirection: 'row', gap: 12, marginTop: 8, flexWrap: 'wrap' },
  badge: { backgroundColor: Colors.primary, color: '#fff', borderRadius: 8, paddingHorizontal: 8, paddingVertical: 2, overflow: 'hidden' },
  code: { color: Colors.text },
  exp: { color: Colors.textSecondary },
  rowActions: { flexDirection: 'row', gap: 10, marginTop: 10 },
  button: { flexGrow: 1, backgroundColor: Colors.accent, padding: 10, borderRadius: 10, alignItems: 'center' },
  buttonDisabled: { backgroundColor: Colors.border, opacity: 0.65 },
  buttonSecondary: { backgroundColor: '#fff', borderWidth: 1, borderColor: Colors.accent },
  buttonText: { color: '#fff', fontWeight: '700' },
  buttonDisabledText: { color: Colors.textSecondary },
  buttonSecondaryText: { color: Colors.accent, fontWeight: '700' },
  modalOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.4)',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    zIndex: 9999,
  },
  modalCard: { width: '100%', maxWidth: 420, backgroundColor: '#fff', borderRadius: 16, padding: 18, borderWidth: 1, borderColor: Colors.border },
  modalTitle: { fontSize: 18, fontWeight: '700', color: Colors.text },
  modalText: { marginTop: 8, color: Colors.textSecondary },
  modalRow: { flexDirection: 'row', gap: 10, marginTop: 16 },
  modalBtn: { flex: 1, borderRadius: 10, paddingVertical: 12, alignItems: 'center' },
  modalCancel: { backgroundColor: '#fff', borderWidth: 1, borderColor: Colors.border },
  modalOk: { backgroundColor: Colors.accent },
  modalBtnText: { fontWeight: '700' },
  modalCancelText: { color: Colors.text },
  modalOkText: { color: '#fff', fontWeight: '700' },
});

