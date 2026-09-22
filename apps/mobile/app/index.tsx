import { useQuery } from '@tanstack/react-query';
import { Box, Column, Heading, Text } from '@personal-library/react-native-components';
import { Link } from 'expo-router';
import { api } from '../src/api/client';

export default function HomeScreen() {
  const health = useQuery({ queryKey: ['health'], queryFn: api.health });
  const state = health.isPending ? 'Checking API…' : health.isSuccess ? 'API connected' : 'API unavailable';

  return (
    <Column gap="md" style={{ flex: 1, justifyContent: 'center', padding: 24 }}>
      <Text>FULL STACK STARTER</Text>
      <Heading level={1}>Build the product.</Heading>
      <Text>A shared Django API for web and mobile, with the native UI foundation already in place.</Text>
      <Box padding="md" radius="md" bg="surface"><Text accessibilityRole="text">{state}</Text></Box>
      <Link href="/account">Open account</Link>
    </Column>
  );
}
