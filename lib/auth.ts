import { getDb } from "./mongodb"
import { compare, hash } from "bcryptjs"
import { SignJWT, jwtVerify } from "jose"
import { cookies } from "next/headers"

const JWT_SECRET = new TextEncoder().encode(process.env.JWT_SECRET || "cropiot-secret-key-change-in-production")

export interface User {
  _id?: string
  name: string
  email: string
  password?: string
  farmName?: string
  location?: string
  createdAt: Date
}

export async function hashPassword(password: string): Promise<string> {
  return hash(password, 12)
}

export async function verifyPassword(password: string, hashedPassword: string): Promise<boolean> {
  return compare(password, hashedPassword)
}

export async function createToken(user: Omit<User, "password">): Promise<string> {
  return new SignJWT({
    id: user._id?.toString(),
    email: user.email,
    name: user.name,
  })
    .setProtectedHeader({ alg: "HS256" })
    .setExpirationTime("7d")
    .sign(JWT_SECRET)
}

export async function verifyToken(token: string) {
  try {
    const { payload } = await jwtVerify(token, JWT_SECRET)
    return payload
  } catch {
    return null
  }
}

export async function getSession() {
  const cookieStore = await cookies()
  const token = cookieStore.get("auth-token")?.value

  if (!token) return null

  return verifyToken(token)
}

export async function createUser(userData: {
  name: string
  email: string
  password: string
  farmName?: string
  location?: string
}): Promise<{ success: boolean; error?: string; user?: User }> {
  try {
    const db = await getDb()
    const users = db.collection("users")

    // Check if user already exists
    const existingUser = await users.findOne({ email: userData.email.toLowerCase() })
    if (existingUser) {
      return { success: false, error: "Email already registered" }
    }

    // Hash password and create user
    const hashedPassword = await hashPassword(userData.password)
    const newUser = {
      name: userData.name,
      email: userData.email.toLowerCase(),
      password: hashedPassword,
      farmName: userData.farmName || "",
      location: userData.location || "",
      createdAt: new Date(),
    }

    const result = await users.insertOne(newUser)

    return {
      success: true,
      user: {
        ...newUser,
        _id: result.insertedId.toString(),
        password: undefined,
      },
    }
  } catch (error) {
    console.error("Create user error:", error)
    return { success: false, error: "Failed to create user" }
  }
}

export async function authenticateUser(
  email: string,
  password: string,
): Promise<{ success: boolean; error?: string; user?: User }> {
  try {
    const db = await getDb()
    const users = db.collection("users")

    const user = await users.findOne({ email: email.toLowerCase() })
    if (!user) {
      return { success: false, error: "Invalid email or password" }
    }

    const isValid = await verifyPassword(password, user.password)
    if (!isValid) {
      return { success: false, error: "Invalid email or password" }
    }

    return {
      success: true,
      user: {
        _id: user._id.toString(),
        name: user.name,
        email: user.email,
        farmName: user.farmName,
        location: user.location,
        createdAt: user.createdAt,
      },
    }
  } catch (error) {
    console.error("Auth error:", error)
    return { success: false, error: "Authentication failed" }
  }
}
