import { MessageSquare, Heart, MessageCircle, TrendingUp, Clock, ThumbsUp } from "lucide-react-native";
import { useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Animated,
  Image,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import Colors from "@/constants/colors";

type PostCategory = "announcement" | "news" | "discussion" | "tips";

type Post = {
  id: string;
  category: PostCategory;
  title: string;
  content: string;
  author: string;
  authorAvatar: string;
  timestamp: number;
  likes: number;
  comments: number;
  isLiked: boolean;
  imageUri?: string;
};

const MOCK_POSTS: Post[] = [
  {
    id: "1",
    category: "announcement",
    title: "🎉 New Recycling Categories Added!",
    content: "We've added support for electronic waste and textile recycling. Start scanning and earn bonus points this week!",
    author: "EcoRecycle Team",
    authorAvatar: "#10B981",
    timestamp: Date.now() - 3600000,
    likes: 124,
    comments: 18,
    isLiked: false,
  },
  {
    id: "2",
    category: "news",
    title: "Global Impact: 1M Tons of Waste Recycled! 🌍",
    content: "Together, our community has helped recycle over 1 million tons of waste! That's equivalent to 500,000 cars off the road for a year.",
    author: "Community Manager",
    authorAvatar: "#3B82F6",
    timestamp: Date.now() - 7200000,
    likes: 892,
    comments: 64,
    isLiked: true,
    imageUri: "https://images.unsplash.com/photo-1532996122724-e3c354a0b15b?w=800",
  },
  {
    id: "3",
    category: "tips",
    title: "Pro Tip: Best Time to Scan for Points",
    content: "Did you know? Scanning during peak hours (6-9 AM) gives you 2x bonus points! Early birds get the rewards 🐦",
    author: "EcoWarrior_42",
    authorAvatar: "#F59E0B",
    timestamp: Date.now() - 14400000,
    likes: 256,
    comments: 42,
    isLiked: false,
  },
  {
    id: "4",
    category: "discussion",
    title: "What's Your Recycling Goal This Month?",
    content: "Let's motivate each other! Share your recycling goals for this month. Mine is to reach 500 scans! 💪",
    author: "GreenLife_Sarah",
    authorAvatar: "#8B5CF6",
    timestamp: Date.now() - 21600000,
    likes: 189,
    comments: 97,
    isLiked: false,
  },
  {
    id: "5",
    category: "news",
    title: "New Partnership with Local Recycling Centers",
    content: "We've partnered with 50+ recycling centers nationwide. Now you can see the nearest drop-off point after each scan!",
    author: "EcoRecycle Team",
    authorAvatar: "#10B981",
    timestamp: Date.now() - 28800000,
    likes: 445,
    comments: 31,
    isLiked: false,
  },
  {
    id: "6",
    category: "tips",
    title: "How to Identify Plastic Types Correctly",
    content: "Look for the recycling symbol with a number (1-7) on plastic items. Each number represents a different type of plastic. Here's a quick guide...",
    author: "RecycleExpert_101",
    authorAvatar: "#EC4899",
    timestamp: Date.now() - 43200000,
    likes: 678,
    comments: 123,
    isLiked: true,
  },
];

export default function ForumScreen() {
  const insets = useSafeAreaInsets();
  const [posts, setPosts] = useState<Post[]>(MOCK_POSTS);
  const [selectedFilter, setSelectedFilter] = useState<"all" | PostCategory>("all");

  const getCategoryColor = (category: PostCategory) => {
    switch (category) {
      case "announcement":
        return "#EF4444";
      case "news":
        return "#3B82F6";
      case "discussion":
        return "#8B5CF6";
      case "tips":
        return "#10B981";
      default:
        return Colors.textSecondary;
    }
  };

  const getCategoryIcon = (category: PostCategory) => {
    switch (category) {
      case "announcement":
        return "📢";
      case "news":
        return "📰";
      case "discussion":
        return "💬";
      case "tips":
        return "💡";
    }
  };

  const handleLike = (postId: string) => {
    setPosts(prev => prev.map(post => 
      post.id === postId 
        ? { ...post, isLiked: !post.isLiked, likes: post.isLiked ? post.likes - 1 : post.likes + 1 }
        : post
    ));
  };

  const getTimeAgo = (timestamp: number) => {
    const seconds = Math.floor((Date.now() - timestamp) / 1000);
    if (seconds < 60) return "just now";
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  };

  const filteredPosts = selectedFilter === "all" 
    ? posts 
    : posts.filter(p => p.category === selectedFilter);

  return (
    <View style={styles.container}>
      <View style={[styles.header, { paddingTop: insets.top + 16 }]}>
        <View style={styles.headerContent}>
          <MessageSquare size={28} color={Colors.primary} />
          <Text style={styles.headerTitle}>Community</Text>
        </View>
        <Text style={styles.headerSubtitle}>News, tips & discussions</Text>
      </View>

      <ScrollView 
        horizontal 
        showsHorizontalScrollIndicator={false}
        style={styles.filterContainer}
        contentContainerStyle={styles.filterContent}
      >
        <TouchableOpacity
          style={[styles.filterChip, selectedFilter === "all" && styles.filterChipActive]}
          onPress={() => setSelectedFilter("all")}
        >
          <Text style={[styles.filterText, selectedFilter === "all" && styles.filterTextActive]}>
            All
          </Text>
        </TouchableOpacity>
        
        <TouchableOpacity
          style={[styles.filterChip, selectedFilter === "announcement" && styles.filterChipActive]}
          onPress={() => setSelectedFilter("announcement")}
        >
          <Text style={[styles.filterText, selectedFilter === "announcement" && styles.filterTextActive]}>
            📢 Announcements
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.filterChip, selectedFilter === "news" && styles.filterChipActive]}
          onPress={() => setSelectedFilter("news")}
        >
          <Text style={[styles.filterText, selectedFilter === "news" && styles.filterTextActive]}>
            📰 News
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.filterChip, selectedFilter === "discussion" && styles.filterChipActive]}
          onPress={() => setSelectedFilter("discussion")}
        >
          <Text style={[styles.filterText, selectedFilter === "discussion" && styles.filterTextActive]}>
            💬 Discussions
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.filterChip, selectedFilter === "tips" && styles.filterChipActive]}
          onPress={() => setSelectedFilter("tips")}
        >
          <Text style={[styles.filterText, selectedFilter === "tips" && styles.filterTextActive]}>
            💡 Tips
          </Text>
        </TouchableOpacity>
      </ScrollView>

      <ScrollView 
        style={styles.postsContainer}
        contentContainerStyle={styles.postsContent}
      >
        {filteredPosts.map((post, index) => {
          const animatedValue = new Animated.Value(0);
          
          Animated.timing(animatedValue, {
            toValue: 1,
            duration: 300,
            delay: index * 50,
            useNativeDriver: true,
          }).start();

          return (
            <Animated.View
              key={post.id}
              style={[
                styles.postCard,
                { opacity: animatedValue },
              ]}
            >
              <View style={styles.postHeader}>
                <View style={[styles.authorAvatar, { backgroundColor: post.authorAvatar }]}>
                  <Text style={styles.avatarText}>
                    {post.author.substring(0, 2).toUpperCase()}
                  </Text>
                </View>
                <View style={styles.postMeta}>
                  <Text style={styles.authorName}>{post.author}</Text>
                  <View style={styles.metaRow}>
                    <View style={[styles.categoryBadge, { backgroundColor: getCategoryColor(post.category) + "20" }]}>
                      <Text style={[styles.categoryText, { color: getCategoryColor(post.category) }]}>
                        {getCategoryIcon(post.category)} {post.category}
                      </Text>
                    </View>
                    <Clock size={12} color={Colors.textLight} />
                    <Text style={styles.timestamp}>{getTimeAgo(post.timestamp)}</Text>
                  </View>
                </View>
              </View>

              <View style={styles.postContent}>
                <Text style={styles.postTitle}>{post.title}</Text>
                <Text style={styles.postText} numberOfLines={3}>{post.content}</Text>
                
                {post.imageUri && (
                  <Image 
                    source={{ uri: post.imageUri }} 
                    style={styles.postImage}
                    resizeMode="cover"
                  />
                )}
              </View>

              <View style={styles.postActions}>
                <TouchableOpacity 
                  style={styles.actionButton}
                  onPress={() => handleLike(post.id)}
                >
                  <Heart 
                    size={20} 
                    color={post.isLiked ? "#EF4444" : Colors.textSecondary}
                    fill={post.isLiked ? "#EF4444" : "none"}
                  />
                  <Text style={[styles.actionText, post.isLiked && styles.actionTextActive]}>
                    {post.likes}
                  </Text>
                </TouchableOpacity>

                <TouchableOpacity style={styles.actionButton}>
                  <MessageCircle size={20} color={Colors.textSecondary} />
                  <Text style={styles.actionText}>{post.comments}</Text>
                </TouchableOpacity>

                <View style={styles.actionButton}>
                  <TrendingUp size={20} color={Colors.textSecondary} />
                </View>
              </View>
            </Animated.View>
          );
        })}

        {filteredPosts.length === 0 && (
          <View style={styles.emptyState}>
            <MessageSquare size={64} color={Colors.textLight} />
            <Text style={styles.emptyText}>No posts in this category</Text>
            <Text style={styles.emptySubtext}>Check back later for updates!</Text>
          </View>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  header: {
    backgroundColor: Colors.surface,
    paddingHorizontal: 20,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  headerContent: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  headerTitle: {
    fontSize: 28,
    fontWeight: "700" as const,
    color: Colors.text,
  },
  headerSubtitle: {
    fontSize: 14,
    color: Colors.textSecondary,
    marginTop: 4,
  },
  filterContainer: {
    backgroundColor: Colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  filterContent: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    gap: 8,
  },
  filterChip: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: Colors.background,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  filterChipActive: {
    backgroundColor: Colors.primary,
    borderColor: Colors.primary,
  },
  filterText: {
    fontSize: 14,
    fontWeight: "600" as const,
    color: Colors.text,
  },
  filterTextActive: {
    color: "#FFFFFF",
  },
  postsContainer: {
    flex: 1,
  },
  postsContent: {
    padding: 16,
    gap: 16,
  },
  postCard: {
    backgroundColor: Colors.surface,
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: Colors.border,
    gap: 16,
  },
  postHeader: {
    flexDirection: "row",
    gap: 12,
  },
  authorAvatar: {
    width: 44,
    height: 44,
    borderRadius: 22,
    justifyContent: "center",
    alignItems: "center",
  },
  avatarText: {
    fontSize: 16,
    fontWeight: "700" as const,
    color: "#FFFFFF",
  },
  postMeta: {
    flex: 1,
    gap: 6,
  },
  authorName: {
    fontSize: 16,
    fontWeight: "600" as const,
    color: Colors.text,
  },
  metaRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  categoryBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  categoryText: {
    fontSize: 12,
    fontWeight: "600" as const,
    textTransform: "capitalize" as const,
  },
  timestamp: {
    fontSize: 12,
    color: Colors.textLight,
  },
  postContent: {
    gap: 12,
  },
  postTitle: {
    fontSize: 18,
    fontWeight: "700" as const,
    color: Colors.text,
    lineHeight: 24,
  },
  postText: {
    fontSize: 15,
    color: Colors.textSecondary,
    lineHeight: 22,
  },
  postImage: {
    width: "100%",
    height: 200,
    borderRadius: 12,
    backgroundColor: Colors.background,
  },
  postActions: {
    flexDirection: "row",
    alignItems: "center",
    gap: 20,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
  },
  actionButton: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  actionText: {
    fontSize: 14,
    fontWeight: "600" as const,
    color: Colors.textSecondary,
  },
  actionTextActive: {
    color: "#EF4444",
  },
  emptyState: {
    alignItems: "center",
    paddingVertical: 64,
    gap: 12,
  },
  emptyText: {
    fontSize: 20,
    fontWeight: "600" as const,
    color: Colors.textSecondary,
  },
  emptySubtext: {
    fontSize: 15,
    color: Colors.textLight,
  },
});
