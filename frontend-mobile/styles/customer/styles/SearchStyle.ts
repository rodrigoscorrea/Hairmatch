import { StyleSheet, Platform } from "react-native";
import { colors } from "@/assets/colors";

export const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    paddingHorizontal: 16,
    paddingTop: 16,
  },
  searchWrapper: {
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#7B3F00",
    borderRadius: 12,
    backgroundColor: "#FFF",
    paddingHorizontal: 8,
    height: 40,
    ...Platform.select({
      web: {
        marginBottom:12
      },
    }),
  },
  input: {
    flex: 1,
    paddingHorizontal: 8,
    color: "#000",
  },
  iconLeft: {
    marginRight: 4,
  },
  iconRight: {
    marginLeft: 4,
  },
  tagContainer: {
    flexDirection: "row",
    marginTop: 12,
    gap: 8,
  },
  tag: {
    borderColor: "#7B3F00",
    borderWidth: 1,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
    backgroundColor: "#FFF",
  },
  tagText: {
    color: "#333",
    fontSize: 14,
  },
  card: {
    flexDirection: "row",
    backgroundColor: "#FFDCC0",
    borderRadius: 16,
    padding: 12,
    alignItems: "center",
    marginBottom: 12,
  },
  avatar: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: "#D9D9D9",
    marginRight: 12,
  },
  info: {
    flex: 1,
  },
  name: {
    fontWeight: "bold",
    fontSize: 16,
    marginBottom: 2,
  },
  ratingRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 4,
  },
  ratingText: {
    marginLeft: 4,
    fontSize: 14,
  },
  locationRow: {
    flexDirection: "row",
    alignItems: "flex-start",
  },
  address: {
    marginLeft: 4,
    fontSize: 12,
    color: "#555",
    flex: 1,
  },
  goButton: {
    padding: 8,
  },
});