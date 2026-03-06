export interface JwtPayload {
    sub : string // user id
    email: string //user email
    exp: number //expiration timestamp
}