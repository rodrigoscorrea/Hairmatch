// The customer's rating as the profile, the agenda and the ratings list show it: "4.3 (3)" or "Sem avaliações".
export const formatCustomerRating = (average: number | null, count: number): string => {
  if (average === null || count === 0) return 'Sem avaliações';
  return `${average.toFixed(1)} (${count})`;
};
