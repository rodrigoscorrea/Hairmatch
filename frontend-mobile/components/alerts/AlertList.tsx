import React from 'react';
import { FlatList, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors } from '@/assets/colors';
import { ErrorModal } from '@/components/modals/ErrorModal/ErrorModal';
import { useAlerts } from '@/hooks/useAlerts';
import { relativeTime } from '@/utils/relative-time';

interface AlertListProps {
  onBack: () => void;
}

/** The inbox of the logged user, the same screen for both roles: only the way back differs. */
export default function AlertList({ onBack }: AlertListProps) {
  const { alerts, unreadCount, isLoaded, busy, open, markAll, errorModal, closeError } = useAlerts();

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.header}>
        <TouchableOpacity onPress={onBack} style={styles.backButton}>
          <Text style={styles.backButtonText}>‹ Voltar</Text>
        </TouchableOpacity>
        <Text style={styles.title}>Notificações</Text>
        <TouchableOpacity
          onPress={markAll}
          disabled={unreadCount === 0 || busy}
          style={[styles.markAll, unreadCount === 0 && styles.markAllDisabled]}
          accessibilityRole="button"
          accessibilityState={{ disabled: unreadCount === 0 || busy }}
        >
          <Text style={[styles.markAllText, unreadCount === 0 && styles.markAllTextDisabled]}>Marcar todas como lidas</Text>
        </TouchableOpacity>
      </View>

      <FlatList
        data={alerts}
        keyExtractor={(item) => item.id.toString()}
        contentContainerStyle={styles.list}
        ListEmptyComponent={isLoaded ? <Text style={styles.emptyText}>Você ainda não tem notificações.</Text> : null}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={[styles.card, item.read ? styles.cardRead : styles.cardUnread]}
            onPress={() => open(item)}
            disabled={busy}
            accessibilityLabel={`${item.read ? '' : 'Não lida. '}${item.title}. ${item.body}`}
          >
            <View style={[styles.marker, item.read && styles.markerRead]} />
            <View style={styles.content}>
              <View style={styles.titleRow}>
                <Text style={[styles.alertTitle, !item.read && styles.alertTitleUnread]} numberOfLines={1}>
                  {item.title}
                </Text>
                <Text style={styles.time}>{relativeTime(item.created_at)}</Text>
              </View>
              <Text style={styles.body}>{item.body}</Text>
            </View>
          </TouchableOpacity>
        )}
      />

      <ErrorModal visible={errorModal.visible} message={errorModal.message} onClose={closeError} />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: colors.background,
  },
  header: {
    paddingHorizontal: 20,
    paddingTop: 10,
    paddingBottom: 10,
  },
  backButton: {
    paddingVertical: 6,
  },
  backButtonText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: colors.details_purple,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
    marginTop: 8,
  },
  markAll: {
    alignSelf: 'flex-start',
    marginTop: 8,
    paddingVertical: 6,
  },
  markAllDisabled: {
    opacity: 0.4,
  },
  markAllText: {
    fontSize: 14,
    fontWeight: 'bold',
    color: colors.details_purple,
  },
  markAllTextDisabled: {
    color: '#666',
  },
  list: {
    paddingHorizontal: 20,
    paddingBottom: 20,
  },
  emptyText: {
    textAlign: 'center',
    color: '#666',
    marginTop: 40,
    fontSize: 15,
  },
  card: {
    flexDirection: 'row',
    borderRadius: 16,
    padding: 12,
    alignItems: 'flex-start',
    marginTop: 12,
  },
  // The unread card has the colored background and the dot; the read one is plain.
  cardUnread: {
    backgroundColor: '#FFDCC0',
  },
  cardRead: {
    backgroundColor: colors.white,
  },
  marker: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: colors.primary,
    marginTop: 5,
    marginRight: 10,
  },
  markerRead: {
    backgroundColor: 'transparent',
  },
  content: {
    flex: 1,
  },
  titleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  alertTitle: {
    flex: 1,
    fontSize: 16,
    color: '#333',
    marginRight: 8,
  },
  alertTitleUnread: {
    fontWeight: 'bold',
  },
  time: {
    fontSize: 12,
    color: '#666',
  },
  body: {
    fontSize: 14,
    color: '#444',
    marginTop: 4,
  },
});
