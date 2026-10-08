import AsyncStorage from '@react-native-async-storage/async-storage';
import React, { useEffect, useState } from 'react';
import { Platform, SafeAreaView, StyleSheet, Text, View } from 'react-native';
import { AmanConsentBanner, AmanConsentClient } from '@aman-consent/react-native';

// Replace these values with the HTTPS API host and the IDs of the separately
// configured iOS and Android properties from the ALAMANE console.
const API_BASE_URL = 'https://cmp.example.ma';
const PROPERTY_IDS = {
  ios: 'REPLACE_WITH_IOS_PROPERTY_ID',
  android: 'REPLACE_WITH_ANDROID_PROPERTY_ID',
};

const platformConfig = Platform.select({
  ios: { channel: 'ios' as const, propertyId: PROPERTY_IDS.ios },
  android: { channel: 'android' as const, propertyId: PROPERTY_IDS.android },
});

if (!platformConfig) {
  throw new Error('Cet exemple ALAMANE prend en charge iOS et Android uniquement.');
}

const client = new AmanConsentClient({
  baseUrl: API_BASE_URL,
  ...platformConfig,
  storage: AsyncStorage,
  requestTimeoutMs: 10_000,
});

/**
 * Integration example only. Replace the state changes with the actual
 * provider's idempotent start/stop APIs, and disable its native auto-start.
 * Do not report consent decisions automatically from this component.
 */
export default function ConsentIntegration() {
  const [analyticsActive, setAnalyticsActive] = useState(false);

  useEffect(() => client.registerPurposeHandler(
    'analytics',
    (context) => {
      // Connect the actual analytics SDK here. Keep the policy context if the
      // provider needs to scope its configuration to this property/version.
      void context;
      setAnalyticsActive(true);
      return () => {
        // Call the provider's supported stop/reset method here.
        setAnalyticsActive(false);
      };
    },
    (_error, _phase) => {
      // Record only a technical lifecycle status; do not include visitor choices.
    },
  ), []);

  return (
    <SafeAreaView style={styles.screen}>
      <View style={styles.content}>
        <Text style={styles.title}>Préférences de confidentialité</Text>
        <AmanConsentBanner
          client={client}
          language="fr"
        />
        <Text style={styles.status}>
          Mesure d’audience : {analyticsActive ? 'active selon la politique' : 'inactive'}
        </Text>
        <Text style={styles.note}>
          Exemple technique fictif : remplacez les identifiants, les textes et les appels fournisseur,
          puis faites valider la politique par votre équipe compétente.
        </Text>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: '#f5f7f6' },
  content: { flex: 1, gap: 16, padding: 20 },
  title: { color: '#173d32', fontSize: 22, fontWeight: '700' },
  status: { color: '#173d32', fontSize: 15 },
  note: { color: '#586761', fontSize: 13, lineHeight: 19 },
});
