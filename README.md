# Documentation API E-commerce

## Table des matières
1. [Authentication](#authentication)
2. [Admin - Categories](#admin---categories)
3. [Admin - Products](#admin---products)
4. [Admin - Vendors](#admin---vendors)
5. [Vendor - Products](#vendor---products)
6. [Vendor - Profile & Sales](#vendor---profile--sales)
7. [Public - Categories & Products](#public---categories--products)
8. [Public - Cart](#public---cart)
9. [Public - Orders](#public---orders)
10. [Delivery - Orders](#delivery---orders)

---

## Authentication

### POST `/token`
**Description :** Connexion pour Admin, Vendeur ou Livreur. Retourne un token JWT à utiliser dans les headers des requêtes authentifiées.

**Accès :** Public

**Body (form-data) :**
```json
{
  "username": "admin",
  "password": "admin123"
}
```

**Response :**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Utilisation du token :**
Ajouter dans les headers des requêtes suivantes :
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Codes d'erreur :**
- `401` : Username ou password incorrect
- `400` : Utilisateur inactif

---

### POST `/register/vendor`
**Description :** Inscription d'un nouveau vendeur. Le vendeur doit être vérifié par un admin avant de pouvoir créer des produits.

**Accès :** Public

**Body :**
```json
{
  "email": "vendeur@example.com",
  "username": "vendeur1",
  "password": "password123",
  "role": "vendor",
  "phone": "+22997123456",
  "business_name": "Ma Boutique",
  "verification_documents": "url_vers_documents_ou_json"
}
```

**Response :**
```json
{
  "id": 2,
  "email": "vendeur@example.com",
  "username": "vendeur1",
  "role": "vendor",
  "is_active": true,
  "is_verified": false,
  "business_name": "Ma Boutique"
}
```

**Notes :**
- `is_verified: false` par défaut → l'admin doit vérifier le vendeur
- Le vendeur ne peut pas créer de produits tant qu'il n'est pas vérifié

**Codes d'erreur :**
- `400` : Email ou username déjà utilisé
- `400` : Role doit être "vendor"

---

## Admin - Categories

### POST `/admin/categories`
**Description :** Créer une nouvelle catégorie de produits. Seul l'admin peut créer des catégories.

**Accès :** Admin uniquement

**Headers :**
```
Authorization: Bearer <token_admin>
```

**Body :**
```json
{
  "name": "Électronique",
  "description": "Appareils électroniques et accessoires"
}
```

**Response :**
```json
{
  "id": 1,
  "name": "Électronique",
  "description": "Appareils électroniques et accessoires"
}
```

**Codes d'erreur :**
- `401` : Token invalide ou manquant
- `403` : Privilèges admin requis

---

### DELETE `/admin/categories/{category_id}`
**Description :** Supprimer une catégorie. Attention : cela peut affecter les produits liés.

**Accès :** Admin uniquement

**Headers :**
```
Authorization: Bearer <token_admin>
```

**Paramètres URL :**
- `category_id` : ID de la catégorie à supprimer

**Response :**
```json
{
  "message": "Category deleted successfully"
}
```

**Codes d'erreur :**
- `404` : Catégorie non trouvée
- `403` : Privilèges admin requis

---

## Admin - Products

### PUT `/admin/products/{product_id}/validate`
**Description :** Valider (approuver) ou rejeter un produit créé par un vendeur. Les produits doivent être approuvés par un admin avant d'être visibles publiquement.

**Accès :** Admin uniquement

**Headers :**
```
Authorization: Bearer <token_admin>
```

**Paramètres URL :**
- `product_id` : ID du produit

**Query Parameters :**
- `approve` : `true` pour approuver, `false` pour rejeter

**Exemple :**
```
PUT /admin/products/5/validate?approve=true
```

**Response :**
```json
{
  "id": 5,
  "name": "iPhone 15",
  "description": "Dernier modèle",
  "price": 450000,
  "stock": 10,
  "status": "approved",
  "category_id": 1,
  "vendor_id": 2
}
```

**Statuts possibles :**
- `pending` : En attente de validation
- `approved` : Approuvé (visible publiquement)
- `rejected` : Rejeté

**Codes d'erreur :**
- `404` : Produit non trouvé
- `403` : Privilèges admin requis

---

## Admin - Vendors

### GET `/admin/vendors/pending`
**Description :** Obtenir la liste de tous les vendeurs en attente de vérification.

**Accès :** Admin uniquement

**Headers :**
```
Authorization: Bearer <token_admin>
```

**Response :**
```json
[
  {
    "id": 2,
    "email": "vendeur@example.com",
    "username": "vendeur1",
    "role": "vendor",
    "is_active": true,
    "is_verified": false,
    "business_name": "Ma Boutique"
  }
]
```

---

### PUT `/admin/vendors/{vendor_id}/verify`
**Description :** Vérifier et activer un vendeur. Une fois vérifié, le vendeur peut créer des produits.

**Accès :** Admin uniquement

**Headers :**
```
Authorization: Bearer <token_admin>
```

**Paramètres URL :**
- `vendor_id` : ID du vendeur

**Response :**
```json
{
  "message": "Vendor verified successfully"
}
```

**Codes d'erreur :**
- `404` : Vendeur non trouvé

---

### DELETE `/admin/vendors/{vendor_id}`
**Description :** Supprimer un vendeur et tous ses produits associés.

**Accès :** Admin uniquement

**Headers :**
```
Authorization: Bearer <token_admin>
```

**Paramètres URL :**
- `vendor_id` : ID du vendeur

**Response :**
```json
{
  "message": "Vendor deleted successfully"
}
```

**Codes d'erreur :**
- `404` : Vendeur non trouvé

---

## Vendor - Products

### POST `/vendor/products`
**Description :** Créer un nouveau produit. Le produit sera en statut "pending" et devra être validé par un admin avant d'être visible. Les admins peuvent créer directement des produits approuvés.

**Accès :** Vendeur vérifié ou Admin

**Headers :**
```
Authorization: Bearer <token_vendor_ou_admin>
```

**Body :**
```json
{
  "name": "iPhone 15 Pro",
  "description": "Dernier modèle Apple avec puce A17",
  "price": 550000,
  "stock": 15,
  "category_id": 1,
  "image_url": "https://example.com/iphone15.jpg"
}
```

**Response :**
```json
{
  "id": 6,
  "name": "iPhone 15 Pro",
  "description": "Dernier modèle Apple avec puce A17",
  "price": 550000,
  "stock": 15,
  "status": "pending",
  "category_id": 1,
  "vendor_id": 2
}
```

**Notes :**
- Vendeur non vérifié → erreur 403
- Produit vendeur → statut "pending"
- Produit admin → statut "approved"

**Codes d'erreur :**
- `403` : Vendeur non vérifié ou non autorisé

---

### PUT `/vendor/products/{product_id}`
**Description :** Modifier un produit existant. Un vendeur ne peut modifier que ses propres produits.

**Accès :** Vendeur (propriétaire) ou Admin

**Headers :**
```
Authorization: Bearer <token_vendor_ou_admin>
```

**Paramètres URL :**
- `product_id` : ID du produit

**Body (tous les champs sont optionnels) :**
```json
{
  "name": "iPhone 15 Pro Max",
  "price": 600000,
  "stock": 20
}
```

**Response :**
```json
{
  "id": 6,
  "name": "iPhone 15 Pro Max",
  "description": "Dernier modèle Apple avec puce A17",
  "price": 600000,
  "stock": 20,
  "status": "pending",
  "category_id": 1,
  "vendor_id": 2
}
```

**Codes d'erreur :**
- `404` : Produit non trouvé
- `403` : Pas autorisé à modifier ce produit

---

### DELETE `/vendor/products/{product_id}`
**Description :** Supprimer un produit. Un vendeur ne peut supprimer que ses propres produits.

**Accès :** Vendeur (propriétaire) ou Admin

**Headers :**
```
Authorization: Bearer <token_vendor_ou_admin>
```

**Paramètres URL :**
- `product_id` : ID du produit

**Response :**
```json
{
  "message": "Product deleted successfully"
}
```

**Codes d'erreur :**
- `404` : Produit non trouvé
- `403` : Pas autorisé à supprimer ce produit

---

## Vendor - Profile & Sales

### PUT `/vendor/location`
**Description :** Définir ou mettre à jour la localisation GPS du vendeur. Utilisé pour calculer la proximité lors de l'assignation des livreurs.

**Accès :** Vendeur ou Admin

**Headers :**
```
Authorization: Bearer <token_vendor>
```

**Query Parameters :**
- `latitude` : Latitude GPS (ex: 6.3703)
- `longitude` : Longitude GPS (ex: 2.3912)

**Exemple :**
```
PUT /vendor/location?latitude=6.3703&longitude=2.3912
```

**Response :**
```json
{
  "message": "Location updated successfully"
}
```

---

### GET `/vendor/sales`
**Description :** Obtenir l'historique de toutes les ventes des produits du vendeur connecté.

**Accès :** Vendeur ou Admin

**Headers :**
```
Authorization: Bearer <token_vendor>
```

**Response :**
```json
[
  {
    "id": 1,
    "order_id": 1,
    "product_id": 6,
    "quantity": 2,
    "price_at_purchase": 550000
  },
  {
    "id": 2,
    "order_id": 2,
    "product_id": 6,
    "quantity": 1,
    "price_at_purchase": 550000
  }
]
```

**Note :** Retourne tous les OrderItems liés aux produits du vendeur.

---

## Public - Categories & Products

### GET `/categories`
**Description :** Obtenir la liste de toutes les catégories disponibles.

**Accès :** Public (pas d'authentification requise)

**Response :**
```json
[
  {
    "id": 1,
    "name": "Électronique",
    "description": "Appareils électroniques et accessoires"
  },
  {
    "id": 2,
    "name": "Mode",
    "description": "Vêtements et accessoires de mode"
  }
]
```

---

### GET `/products`
**Description :** Obtenir la liste de tous les produits approuvés. Peut être filtré par catégorie.

**Accès :** Public

**Query Parameters (optionnels) :**
- `category_id` : Filtrer par ID de catégorie

**Exemples :**
```
GET /products
GET /products?category_id=1
```

**Response :**
```json
[
  {
    "id": 6,
    "name": "iPhone 15 Pro",
    "description": "Dernier modèle Apple",
    "price": 550000,
    "stock": 15,
    "status": "approved",
    "category_id": 1,
    "vendor_id": 2
  }
]
```

**Note :** Seuls les produits avec `status = "approved"` sont retournés.

---

### GET `/products/{product_id}`
**Description :** Obtenir les détails d'un produit spécifique.

**Accès :** Public

**Paramètres URL :**
- `product_id` : ID du produit

**Response :**
```json
{
  "id": 6,
  "name": "iPhone 15 Pro",
  "description": "Dernier modèle Apple avec puce A17",
  "price": 550000,
  "stock": 15,
  "status": "approved",
  "category_id": 1,
  "vendor_id": 2
}
```

**Codes d'erreur :**
- `404` : Produit non trouvé ou non approuvé

---

## Public - Cart

### POST `/cart`
**Description :** Ajouter un produit au panier d'un utilisateur anonyme. Le panier est identifié par un `session_id` unique généré côté client.

**Accès :** Public

**Body :**
```json
{
  "session_id": "anonymous_user_12345",
  "product_id": 6,
  "quantity": 2
}
```

**Notes :**
- `session_id` : Identifiant unique généré côté client (ex: UUID)
- Si le produit existe déjà dans le panier, la quantité est ajoutée

**Response :**
```json
{
  "id": 1,
  "product_id": 6,
  "quantity": 2,
  "product": {
    "id": 6,
    "name": "iPhone 15 Pro",
    "price": 550000,
    "stock": 15,
    "status": "approved",
    "category_id": 1,
    "vendor_id": 2
  }
}
```

**Codes d'erreur :**
- `404` : Produit non trouvé

---

### GET `/cart/{session_id}`
**Description :** Voir tous les articles du panier d'un utilisateur anonyme.

**Accès :** Public

**Paramètres URL :**
- `session_id` : Identifiant de session

**Response :**
```json
[
  {
    "id": 1,
    "product_id": 6,
    "quantity": 2,
    "product": {
      "id": 6,
      "name": "iPhone 15 Pro",
      "price": 550000,
      "stock": 15,
      "status": "approved",
      "category_id": 1,
      "vendor_id": 2
    }
  },
  {
    "id": 2,
    "product_id": 8,
    "quantity": 1,
    "product": {
      "id": 8,
      "name": "Samsung Galaxy S24",
      "price": 480000,
      "stock": 20,
      "status": "approved",
      "category_id": 1,
      "vendor_id": 3
    }
  }
]
```

---

### DELETE `/cart/{session_id}/{item_id}`
**Description :** Supprimer un article spécifique du panier.

**Accès :** Public

**Paramètres URL :**
- `session_id` : Identifiant de session
- `item_id` : ID de l'article dans le panier

**Response :**
```json
{
  "message": "Item removed from cart"
}
```

**Codes d'erreur :**
- `404` : Article non trouvé dans le panier

---

## Public - Orders

### POST `/orders`
**Description :** Créer une commande à partir du panier. Le client fournit ses informations et sa localisation. Le panier est vidé après création de la commande.

**Accès :** Public

**Body :**
```json
{
  "session_id": "anonymous_user_12345",
  "client_name": "Jean Dupont",
  "client_email": "jean.dupont@example.com",
  "client_phone": "+22997123456",
  "client_address": "Rue 123, Cotonou",
  "client_latitude": 6.3703,
  "client_longitude": 2.3912
}
```

**Response :**
```json
{
  "id": 1,
  "order_number": "ORD-20250121143025",
  "client_name": "Jean Dupont",
  "total_amount": 1100000,
  "status": "pending",
  "created_at": "2025-01-21T14:30:25.123456"
}
```

**Processus :**
1. Récupère tous les articles du panier
2. Calcule le montant total
3. Crée la commande avec statut "pending"
4. Crée les OrderItems
5. Vide le panier

**Statuts de commande :**
- `pending` : En attente de paiement
- `paid` : Payée
- `assigned` : Livreur assigné
- `in_delivery` : En cours de livraison
- `delivered` : Livrée
- `cancelled` : Annulée

**Codes d'erreur :**
- `400` : Panier vide

---

### POST `/orders/{order_id}/payment`
**Description :** Traiter le paiement d'une commande via Fedapay et assigner automatiquement un livreur basé sur la proximité GPS.

**Accès :** Public

**Paramètres URL :**
- `order_id` : ID de la commande

**Query Parameters :**
- `payment_reference` : Référence de transaction Fedapay

**Exemple :**
```
POST /orders/1/payment?payment_reference=FEDAPAY_TXN_123456
```

**Response :**
```json
{
  "message": "Payment processed and delivery assigned",
  "order_id": 1
}
```

**Processus :**
1. Marque la commande comme "paid"
2. Enregistre la référence Fedapay
3. Récupère les vendeurs des produits commandés
4. Trouve tous les livreurs actifs
5. Calcule la distance entre vendeur et client pour chaque livreur
6. Assigne le livreur le plus proche
7. Change le statut en "assigned"

**Algorithme de proximité :**
- Utilise la formule de Haversine pour calculer la distance GPS
- Sélectionne le livreur avec la distance minimale
- Si aucun livreur n'a de localisation GPS, pas d'assignation automatique

**Codes d'erreur :**
- `404` : Commande non trouvée

---

### GET `/orders/global-sales`
**Description :** Obtenir l'historique global de toutes les ventes sur la plateforme (tous vendeurs confondus).

**Accès :** Public

**Response :**
```json
[
  {
    "id": 1,
    "order_id": 1,
    "product_id": 6,
    "quantity": 2,
    "price_at_purchase": 550000
  },
  {
    "id": 2,
    "order_id": 1,
    "product_id": 8,
    "quantity": 1,
    "price_at_purchase": 480000
  }
]
```

**Note :** Utile pour les statistiques globales de la plateforme.

---

## Delivery - Orders

### GET `/delivery/orders`
**Description :** Obtenir la liste des livraisons assignées au livreur connecté (statuts "assigned" ou "in_delivery").

**Accès :** Livreur uniquement

**Headers :**
```
Authorization: Bearer <token_livreur>
```

**Response :**
```json
[
  {
    "id": 1,
    "order_number": "ORD-20250121143025",
    "client_name": "Jean Dupont",
    "client_email": "jean.dupont@example.com",
    "client_phone": "+22997123456",
    "client_address": "Rue 123, Cotonou",
    "client_latitude": 6.3703,
    "client_longitude": 2.3912,
    "total_amount": 1100000,
    "status": "assigned",
    "delivery_person_id": 4,
    "created_at": "2025-01-21T14:30:25.123456"
  }
]
```

**Codes d'erreur :**
- `403` : Accès réservé aux livreurs

---

### PUT `/delivery/orders/{order_id}/status`
**Description :** Mettre à jour le statut d'une livraison. Le livreur ne peut modifier que ses propres livraisons.

**Accès :** Livreur uniquement

**Headers :**
```
Authorization: Bearer <token_livreur>
```

**Paramètres URL :**
- `order_id` : ID de la commande

**Query Parameters :**
- `new_status` : Nouveau statut (`in_delivery`, `delivered`, `cancelled`)

**Exemple :**
```
PUT /delivery/orders/1/status?new_status=in_delivery
```

**Response :**
```json
{
  "message": "Status updated successfully"
}
```

**Notes :**
- Si `new_status = "delivered"`, le champ `delivered_at` est automatiquement rempli
- Le livreur ne peut modifier que les commandes qui lui sont assignées

**Codes d'erreur :**
- `404` : Commande non trouvée ou non assignée à ce livreur
- `403` : Accès réservé aux livreurs

---

## Flux complet d'utilisation

### 1. Client anonyme fait des achats
```
1. GET /categories → Voir les catégories
2. GET /products?category_id=1 → Voir les produits d'une catégorie
3. GET /products/6 → Voir détails d'un produit
4. POST /cart → Ajouter au panier (avec session_id)
5. GET /cart/{session_id} → Voir le panier
6. POST /orders → Créer la commande avec infos client
7. POST /orders/1/payment → Payer (Fedapay) → Livreur assigné automatiquement
```

### 2. Vendeur s'inscrit et vend
```
1. POST /register/vendor → S'inscrire
2. [Admin valide avec PUT /admin/vendors/{id}/verify]
3. POST /token → Se connecter
4. PUT /vendor/location → Définir sa localisation
5. POST /vendor/products → Créer un produit (status: pending)
6. [Admin valide avec PUT /admin/products/{id}/validate?approve=true]
7. GET /vendor/sales → Consulter ses ventes
```

### 3. Admin gère la plateforme
```
1. POST /token → Se connecter
2. GET /admin/vendors/pending → Voir vendeurs à vérifier
3. PUT /admin/vendors/{id}/verify → Vérifier un vendeur
4. POST /admin/categories → Créer des catégories
5. PUT /admin/products/{id}/validate → Valider produits vendeurs
6. DELETE /admin/vendors/{id} → Supprimer un vendeur si nécessaire
```

### 4. Livreur gère ses livraisons
```
1. POST /token → Se connecter
2. GET /delivery/orders → Voir livraisons assignées
3. PUT /delivery/orders/{id}/status?new_status=in_delivery → Démarrer livraison
4. PUT /delivery/orders/{id}/status?new_status=delivered → Confirmer livraison
```

---

## Codes HTTP utilisés

- `200` : Succès
- `201` : Ressource créée
- `400` : Requête invalide (données manquantes, panier vide, etc.)
- `401` : Non authentifié (token manquant ou invalide)
- `403` : Non autorisé (pas les bons privilèges)
- `404` : Ressource non trouvée
- `500` : Erreur serveur

---

## Notes de sécurité

1. **JWT Token** : Expire après 30 minutes, doit être renouvelé
2. **Passwords** : Hachés avec bcrypt
3. **Session IDs** : Générés côté client (UUID recommandé)
4. **CORS** : À configurer selon vos besoins
5. **HTTPS** : Obligatoire en production
6. **Rate limiting** : À implémenter pour éviter les abus

---

## Intégration Fedapay (À compléter)

L'endpoint `/orders/{order_id}/payment` doit être complété avec l'intégration réelle de Fedapay :

```python
import requests

# Dans l'endpoint payment
fedapay_response = requests.post(
    "https://api.fedapay.com/v1/transactions",
    headers={"Authorization": f"Bearer {FEDAPAY_SECRET_KEY}"},
    json={
        "amount": order.total_amount,
        "currency": "XOF",
        "description": f"Commande {order.order_number}",
        "callback_url": "https://votre-api.com/payment-callback"
    }
)

if fedapay_response.status_code == 200:
    # Paiement réussi
    order.payment_reference = fedapay_response.json()["transaction_id"]
else:
    # Gérer l'erreur
    raise HTTPException(status_code=400, detail="Payment failed")
```

Documentation Fedapay : https://docs.fedapay.com/
